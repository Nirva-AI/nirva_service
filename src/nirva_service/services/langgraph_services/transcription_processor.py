"""
Background processor for analyzing transcriptions from the database.
Runs periodically to process pending transcriptions through the incremental analyzer.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from ...db.pgsql_client import SessionLocal
from ...db.pgsql_object import TranscriptionResultDB
from ..app_services.incremental_analyzer import IncrementalAnalyzer
from .langgraph_service import LanggraphService


class TranscriptionProcessor:
    """Processes pending transcriptions from the database."""
    
    def __init__(
        self, 
        langgraph_service: LanggraphService,
        process_interval_seconds: int = 120,  # 2 minutes
        max_transcriptions_per_batch: int = 1000
    ):
        """
        Initialize the transcription processor.
        
        Args:
            langgraph_service: Service for LLM interactions
            process_interval_seconds: How often to check for pending transcriptions
            max_transcriptions_per_batch: Maximum transcriptions to process in one batch
        """
        self.langgraph_service = langgraph_service
        self.incremental_analyzer = IncrementalAnalyzer(langgraph_service)
        self.process_interval = process_interval_seconds
        self.max_batch_size = max_transcriptions_per_batch
        self.is_running = False
        self._task = None
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_failed": 0,
            "last_run": None,
            "last_error": None,
            "processing_time_ms": 0
        }
    
    
    async def start(self):
        """Start the background processing task."""
        if self.is_running:
            logger.warning("Transcription processor already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._background_process())
        logger.info(
            f"Transcription processor started, checking every {self.process_interval} seconds"
        )
    
    
    async def stop(self):
        """Stop the background processing task."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Transcription processor stopped")
    
    
    async def _background_process(self):
        """Main background processing loop."""
        logger.info("Starting transcription processor background task...")
        
        while self.is_running:
            try:
                start_time = datetime.utcnow()
                
                # Process pending transcriptions
                processed_count = await self._process_pending_transcriptions()
                
                # Update statistics
                processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self.stats["processing_time_ms"] = processing_time
                self.stats["last_run"] = datetime.utcnow().isoformat()
                
                if processed_count > 0:
                    logger.info(
                        f"Processed {processed_count} transcription groups in {processing_time:.0f}ms"
                    )
                
                # Wait for next interval
                await asyncio.sleep(self.process_interval)
                
            except Exception as e:
                logger.error(f"Error in transcription processor: {e}")
                self.stats["last_error"] = str(e)
                await asyncio.sleep(self.process_interval)
    
    
    async def _process_pending_transcriptions(self) -> int:
        """
        Process all pending transcriptions.
        
        Returns:
            Number of user/date groups processed
        """
        db: Session = SessionLocal()
        processed_groups = 0
        
        try:
            # Get pending transcriptions grouped by user and date
            pending_groups = self._get_pending_transcription_groups(db)
            
            if not pending_groups:
                return 0
            
            logger.info(f"Found {len(pending_groups)} user/date groups to process")
            
            # Process each group
            for (username, date_str), transcriptions in pending_groups.items():
                try:
                    await self._process_user_date_group(
                        db, username, date_str, transcriptions
                    )
                    processed_groups += 1
                    
                except Exception as e:
                    logger.error(
                        f"Failed to process group {username}/{date_str}: {e}"
                    )
                    self._mark_transcriptions_failed(db, transcriptions, str(e))
                    self.stats["total_failed"] += len(transcriptions)
            
            return processed_groups
            
        finally:
            db.close()
    
    
    def _get_pending_transcription_groups(
        self, db: Session
    ) -> Dict[Tuple[str, str], List[TranscriptionResultDB]]:
        """
        Get pending transcriptions grouped by username and date.
        
        Returns:
            Dictionary mapping (username, date) to list of transcriptions
        """
        # Query pending transcriptions
        pending = db.query(TranscriptionResultDB).filter(
            TranscriptionResultDB.analysis_status == "pending"
        ).order_by(
            TranscriptionResultDB.username,
            TranscriptionResultDB.start_time
        ).limit(self.max_batch_size).all()
        
        if not pending:
            return {}
        
        # Group by username and date
        groups = defaultdict(list)
        for transcription in pending:
            # Extract date from start_time
            date_str = transcription.start_time.strftime("%Y-%m-%d")
            key = (transcription.username, date_str)
            groups[key].append(transcription)
        
        return dict(groups)
    
    
    async def _process_user_date_group(
        self,
        db: Session,
        username: str,
        date_str: str,
        transcriptions: List[TranscriptionResultDB]
    ):
        """
        Process all transcriptions for a specific user and date.
        Makes ONE LLM call for all transcriptions combined.
        """
        logger.info(
            f"Processing {len(transcriptions)} transcriptions for "
            f"user {username[:8]}... on {date_str}"
        )
        
        # Mark as processing
        for trans in transcriptions:
            trans.analysis_status = "processing"
        db.commit()
        
        try:
            # Sort by start time to maintain chronological order
            sorted_trans = sorted(transcriptions, key=lambda x: x.start_time)
            
            # Concatenate all transcriptions with time markers
            combined_text = self._concatenate_transcriptions(sorted_trans)
            
            if not combined_text or len(combined_text.strip()) <= 1:
                logger.warning(
                    f"Empty combined text for {username}/{date_str}, marking as completed"
                )
                # Mark as completed even if empty (no need to retry)
                for trans in transcriptions:
                    trans.analysis_status = "completed"
                    trans.analyzed_at = datetime.utcnow()
                db.commit()
                return
            
            # Process through incremental analyzer (ONE LLM call)
            logger.info(
                f"Sending {len(combined_text)} chars to analyzer for {username}/{date_str}"
            )
            
            result = await self.incremental_analyzer.process_incremental_transcript(
                username=username,
                time_stamp=date_str,
                new_transcript=combined_text
            )
            
            # Mark all transcriptions as completed
            for trans in transcriptions:
                trans.analysis_status = "completed"
                trans.analyzed_at = datetime.utcnow()
            
            db.commit()
            
            # Update statistics
            self.stats["total_processed"] += len(transcriptions)
            
            logger.info(
                f"Successfully analyzed {username}/{date_str}: "
                f"{result.new_events_count} new events, "
                f"{result.updated_events_count} updated events, "
                f"{result.total_events_count} total events"
            )
            
        except Exception as e:
            # Mark as failed on error
            logger.error(f"Analysis failed for {username}/{date_str}: {e}")
            for trans in transcriptions:
                trans.analysis_status = "failed"
            db.commit()
            raise
    
    
    def _concatenate_transcriptions(
        self, transcriptions: List[TranscriptionResultDB]
    ) -> str:
        """
        Concatenate multiple transcriptions with time markers.
        
        Args:
            transcriptions: List of transcriptions sorted by time
            
        Returns:
            Combined text with time markers
        """
        parts = []
        
        for trans in transcriptions:
            # Format time marker
            time_str = trans.start_time.strftime("%H:%M")
            
            # Get transcription text
            text = trans.transcription_text.strip()
            
            if text:
                # Add time marker and text
                parts.append(f"[{time_str}] {text}")
        
        # Join with space for natural flow
        return " ".join(parts)
    
    
    def _mark_transcriptions_failed(
        self,
        db: Session,
        transcriptions: List[TranscriptionResultDB],
        error_msg: str
    ):
        """Mark transcriptions as failed."""
        try:
            for trans in transcriptions:
                trans.analysis_status = "failed"
            db.commit()
        except Exception as e:
            logger.error(f"Failed to mark transcriptions as failed: {e}")
            db.rollback()
    
    
    async def trigger_manual_processing(self) -> Dict:
        """
        Manually trigger processing (useful for testing).
        
        Returns:
            Processing results
        """
        logger.info("Manual processing triggered")
        
        start_time = datetime.utcnow()
        processed_count = await self._process_pending_transcriptions()
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "processed_groups": processed_count,
            "processing_time_ms": processing_time,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    
    def get_status(self) -> Dict:
        """
        Get current processor status.
        
        Returns:
            Status dictionary
        """
        db: Session = SessionLocal()
        try:
            # Get counts by status
            pending_count = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.analysis_status == "pending"
            ).count()
            
            processing_count = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.analysis_status == "processing"
            ).count()
            
            completed_count = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.analysis_status == "completed"
            ).count()
            
            failed_count = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.analysis_status == "failed"
            ).count()
            
            return {
                "is_running": self.is_running,
                "process_interval_seconds": self.process_interval,
                "max_batch_size": self.max_batch_size,
                "counts": {
                    "pending": pending_count,
                    "processing": processing_count,
                    "completed": completed_count,
                    "failed": failed_count
                },
                "statistics": self.stats
            }
            
        finally:
            db.close()
    
    
    def get_statistics(self) -> Dict:
        """
        Get detailed statistics.
        
        Returns:
            Statistics dictionary
        """
        db: Session = SessionLocal()
        try:
            # Get more detailed statistics
            today = datetime.utcnow().date()
            
            # Today's processing
            today_completed = db.query(TranscriptionResultDB).filter(
                and_(
                    TranscriptionResultDB.analysis_status == "completed",
                    func.date(TranscriptionResultDB.analyzed_at) == today
                )
            ).count()
            
            # Get unique users processed today
            unique_users_today = db.query(
                func.count(func.distinct(TranscriptionResultDB.username))
            ).filter(
                and_(
                    TranscriptionResultDB.analysis_status == "completed",
                    func.date(TranscriptionResultDB.analyzed_at) == today
                )
            ).scalar()
            
            # Get oldest pending transcription
            oldest_pending = db.query(TranscriptionResultDB).filter(
                TranscriptionResultDB.analysis_status == "pending"
            ).order_by(TranscriptionResultDB.start_time).first()
            
            oldest_pending_age = None
            if oldest_pending:
                age = datetime.utcnow() - oldest_pending.created_at.replace(tzinfo=None)
                oldest_pending_age = age.total_seconds()
            
            return {
                "today": {
                    "completed_transcriptions": today_completed,
                    "unique_users": unique_users_today
                },
                "all_time": {
                    "total_processed": self.stats["total_processed"],
                    "total_failed": self.stats["total_failed"]
                },
                "pending": {
                    "oldest_age_seconds": oldest_pending_age
                },
                "performance": {
                    "last_processing_time_ms": self.stats["processing_time_ms"],
                    "last_run": self.stats["last_run"],
                    "last_error": self.stats["last_error"]
                }
            }
            
        finally:
            db.close()