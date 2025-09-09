#!/usr/bin/env python3
"""
Script to reset transcriptions and delete events for specific dates.
This allows the analyzer to reprocess the transcriptions and regenerate events.

Usage:
    python scripts/reset_transcriptions_for_reprocessing.py --username yytestbot --dates 2025-09-08,2025-09-09
    python scripts/reset_transcriptions_for_reprocessing.py --username yytestbot --date-range 2025-09-08:2025-09-10
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from loguru import logger

from nirva_service.db.pgsql_object import (
    EventDB,
    TranscriptionResultDB,
    MentalStateScoreDB,
)
from nirva_service.db.pgsql_client import SessionLocal


def parse_dates(date_str: str = None, date_range: str = None) -> List[datetime]:
    """Parse date arguments and return list of dates to process."""
    dates = []
    
    if date_str:
        # Parse comma-separated dates
        for date_part in date_str.split(","):
            try:
                date = datetime.strptime(date_part.strip(), "%Y-%m-%d")
                dates.append(date)
            except ValueError:
                logger.error(f"Invalid date format: {date_part}. Use YYYY-MM-DD")
                sys.exit(1)
    
    elif date_range:
        # Parse date range (start:end)
        try:
            start_str, end_str = date_range.split(":")
            start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d")
            end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
            
            current_date = start_date
            while current_date <= end_date:
                dates.append(current_date)
                current_date += timedelta(days=1)
        except (ValueError, IndexError):
            logger.error(f"Invalid date range format: {date_range}. Use YYYY-MM-DD:YYYY-MM-DD")
            sys.exit(1)
    
    return dates


def reset_transcriptions_for_dates(
    username: str,
    dates: List[datetime],
    dry_run: bool = False
) -> None:
    """Reset transcriptions and delete events for specified dates."""
    
    db = SessionLocal()
    try:
        for date in dates:
            # Define date range (full day in UTC)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
            
            logger.info(f"Processing date: {date.strftime('%Y-%m-%d')} for user: {username}")
            
            # 1. Find and reset transcriptions
            transcriptions = db.query(TranscriptionResultDB).filter(
                and_(
                    TranscriptionResultDB.username == username,
                    TranscriptionResultDB.start_time >= start_of_day,
                    TranscriptionResultDB.start_time <= end_of_day
                )
            ).all()
            
            transcription_count = len(transcriptions)
            logger.info(f"Found {transcription_count} transcriptions to reset")
            
            if not dry_run:
                for trans in transcriptions:
                    trans.analysis_status = "pending"
                    trans.analyzed_at = None
                    logger.debug(f"Reset transcription: {trans.id} ({trans.start_time})")
            
            # 2. Delete events for this date
            events = db.query(EventDB).filter(
                and_(
                    EventDB.username == username,
                    EventDB.start_timestamp >= start_of_day,
                    EventDB.start_timestamp <= end_of_day
                )
            ).all()
            
            event_count = len(events)
            event_ids = [event.event_id for event in events]
            logger.info(f"Found {event_count} events to delete: {event_ids}")
            
            if not dry_run:
                for event in events:
                    db.delete(event)
                    logger.debug(f"Deleted event: {event.event_id}")
            
            # 3. Delete mental state scores linked to these events
            if event_ids and not dry_run:
                mental_scores = db.query(MentalStateScoreDB).filter(
                    and_(
                        MentalStateScoreDB.event_id.in_(event_ids),
                        MentalStateScoreDB.data_source == "event"
                    )
                ).all()
                
                score_count = len(mental_scores)
                logger.info(f"Found {score_count} mental state scores to delete")
                
                for score in mental_scores:
                    db.delete(score)
                    logger.debug(f"Deleted mental state score: {score.id}")
            
            # 4. Also delete any mental state scores for this date (even without event_id)
            mental_scores_by_date = db.query(MentalStateScoreDB).filter(
                and_(
                    func.date(MentalStateScoreDB.timestamp) == date.date(),
                    MentalStateScoreDB.user_id.in_(
                        db.query(EventDB.user_id).filter(EventDB.username == username).subquery()
                    )
                )
            ).all()
            
            if mental_scores_by_date:
                score_count = len(mental_scores_by_date)
                logger.info(f"Found {score_count} additional mental state scores for this date")
                
                if not dry_run:
                    for score in mental_scores_by_date:
                        db.delete(score)
            
            logger.info(f"Summary for {date.strftime('%Y-%m-%d')}:")
            logger.info(f"  - Transcriptions reset: {transcription_count}")
            logger.info(f"  - Events deleted: {event_count}")
            if not dry_run:
                logger.info("  - Changes committed to database")
            else:
                logger.info("  - DRY RUN: No changes made")
        
        if not dry_run:
            db.commit()
            logger.success("All changes committed successfully!")
        else:
            logger.warning("DRY RUN completed. Use --execute to apply changes.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Reset transcriptions and delete events for reprocessing"
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Username to reset transcriptions for"
    )
    parser.add_argument(
        "--dates",
        help="Comma-separated list of dates (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--date-range",
        help="Date range in format YYYY-MM-DD:YYYY-MM-DD"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the changes (default is dry run)"
    )
    
    args = parser.parse_args()
    
    if not args.dates and not args.date_range:
        logger.error("Either --dates or --date-range must be specified")
        sys.exit(1)
    
    if args.dates and args.date_range:
        logger.error("Cannot specify both --dates and --date-range")
        sys.exit(1)
    
    # Parse dates
    dates = parse_dates(args.dates, args.date_range)
    
    if not dates:
        logger.error("No valid dates found")
        sys.exit(1)
    
    # Run the reset
    reset_transcriptions_for_dates(
        username=args.username,
        dates=dates,
        dry_run=not args.execute
    )


if __name__ == "__main__":
    main()