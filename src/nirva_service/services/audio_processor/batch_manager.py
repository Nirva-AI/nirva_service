"""
Batch manager for accumulating audio segments before transcription.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4
from loguru import logger
from sqlalchemy.orm import Session

from nirva_service.db.pgsql_client import SessionLocal
from nirva_service.db.pgsql_object import AudioFileDB, AudioBatchDB


class BatchManager:
    """Manages batching of audio segments for transcription."""
    
    def __init__(self, max_gap_seconds: int = 300, timeout_seconds: int = 300):
        """
        Initialize batch manager.
        
        Args:
            max_gap_seconds: Maximum gap between segments to consider same batch (default: 5 minutes)
            timeout_seconds: Time after which to process a batch (default: 5 minutes)
        """
        self.max_gap = timedelta(seconds=max_gap_seconds)
        self.timeout = timedelta(seconds=timeout_seconds)
        
    def get_or_create_batch(self, username: str, segment_time: datetime, db: Session) -> AudioBatchDB:
        """
        Get active batch for user or create new one.
        
        Args:
            username: Session identifier
            segment_time: Upload time of the segment
            db: Database session
            
        Returns:
            Active or new batch
        """
        # Find active batch for this user
        active_batch = db.query(AudioBatchDB).filter(
            AudioBatchDB.username == username,
            AudioBatchDB.status == "accumulating"
        ).first()
        
        if active_batch:
            # Check if segment belongs to this batch (within max_gap)
            time_since_last = segment_time - active_batch.last_segment_time
            
            if time_since_last > self.max_gap:
                logger.info(
                    f"Gap of {time_since_last.total_seconds():.1f}s exceeds max_gap "
                    f"({self.max_gap.total_seconds():.1f}s), creating new batch for {username}"
                )
                # Gap too large, this is a new conversation
                active_batch = self._create_new_batch(username, segment_time, db)
            else:
                logger.debug(
                    f"Adding segment to existing batch for {username}, "
                    f"gap: {time_since_last.total_seconds():.1f}s"
                )
        else:
            # No active batch, create new one
            logger.info(f"Creating first batch for {username}")
            active_batch = self._create_new_batch(username, segment_time, db)
        
        return active_batch
    
    def _create_new_batch(self, username: str, segment_time: datetime, db: Session) -> AudioBatchDB:
        """Create a new batch."""
        batch = AudioBatchDB(
            username=username,
            first_segment_time=segment_time,
            last_segment_time=segment_time,
            status="accumulating",
            segment_count=0,
            total_speech_duration=0.0
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        logger.info(f"Created new batch {batch.id} for {username}")
        return batch
    
    def add_segment_to_batch(
        self,
        batch: AudioBatchDB,
        audio_file: AudioFileDB,
        speech_duration: float,
        db: Session
    ) -> None:
        """
        Add a segment to the batch.
        
        Args:
            batch: The batch to add to
            audio_file: The audio file to add
            speech_duration: Duration of speech in the segment
            db: Database session
        """
        # Link audio file to batch
        audio_file.batch_id = batch.id
        
        # Update batch statistics
        batch.segment_count += 1
        batch.total_speech_duration += speech_duration
        batch.last_segment_time = audio_file.uploaded_at
        
        db.commit()
        
        logger.debug(
            f"Added segment to batch {batch.id}: "
            f"segments={batch.segment_count}, "
            f"speech={batch.total_speech_duration:.1f}s"
        )
    
    def get_batches_ready_for_processing(self, db: Session) -> List[AudioBatchDB]:
        """
        Get all batches that have exceeded timeout and are ready for processing.
        
        Args:
            db: Database session
            
        Returns:
            List of batches ready for processing
        """
        from datetime import timezone
        current_time = datetime.now(timezone.utc)
        timeout_threshold = current_time - self.timeout
        
        # Find batches that have timed out
        ready_batches = db.query(AudioBatchDB).filter(
            AudioBatchDB.status == "accumulating",
            AudioBatchDB.first_segment_time <= timeout_threshold
        ).all()
        
        if ready_batches:
            logger.info(f"Found {len(ready_batches)} batches ready for processing")
            for batch in ready_batches:
                elapsed = (current_time - batch.first_segment_time).total_seconds()
                logger.debug(
                    f"Batch {batch.id} ready: {batch.segment_count} segments, "
                    f"elapsed: {elapsed:.1f}s"
                )
        
        return ready_batches
    
    def mark_batch_processing(self, batch: AudioBatchDB, db: Session) -> None:
        """Mark batch as processing to prevent duplicate processing."""
        batch.status = "processing"
        db.commit()
        logger.info(f"Marked batch {batch.id} as processing")
    
    def mark_batch_completed(self, batch: AudioBatchDB, db: Session) -> None:
        """Mark batch as completed."""
        from datetime import timezone
        batch.status = "completed"
        batch.processed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Marked batch {batch.id} as completed")
    
    def get_batch_segments(self, batch: AudioBatchDB, db: Session) -> List[AudioFileDB]:
        """
        Get all audio segments belonging to a batch.
        
        Args:
            batch: The batch to get segments for
            db: Database session
            
        Returns:
            List of audio files in the batch, ordered by upload time
        """
        segments = db.query(AudioFileDB).filter(
            AudioFileDB.batch_id == batch.id
        ).order_by(AudioFileDB.uploaded_at).all()
        
        logger.debug(f"Retrieved {len(segments)} segments for batch {batch.id}")
        return segments


# Singleton instance
_batch_manager: Optional[BatchManager] = None


def get_batch_manager(
    max_gap_seconds: Optional[int] = None,
    timeout_seconds: Optional[int] = None
) -> BatchManager:
    """Get or create the singleton batch manager instance."""
    global _batch_manager
    if _batch_manager is None:
        max_gap = max_gap_seconds or int(os.getenv('BATCH_MAX_GAP_SECONDS', '300'))
        timeout = timeout_seconds or int(os.getenv('BATCH_TIMEOUT_SECONDS', '300'))
        _batch_manager = BatchManager(max_gap, timeout)
    return _batch_manager