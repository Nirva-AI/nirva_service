#!/usr/bin/env python3
"""
Reusable script to reset events and transcriptions for a user within a date range.
This is useful for regenerating events after fixing analyzer logic.

Usage:
    python reset_events_and_transcripts.py --username yytestbot --start-date 2025-09-08 --end-date 2025-09-09 --timezone PDT --execute
    
    Without --execute, it will show what would be deleted (dry run)
"""

import os
import sys
import argparse
from datetime import datetime
import pytz

# Add src to path so we can import nirva modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from nirva_service.db.pgsql_client import SessionLocal
from nirva_service.db.pgsql_object import EventDB, TranscriptionResultDB


def parse_args():
    parser = argparse.ArgumentParser(description='Reset events and transcriptions for reprocessing')
    parser.add_argument('--username', required=True, help='Username to reset events for')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--timezone', default='UTC', help='Timezone (e.g., UTC, PDT, EST)')
    parser.add_argument('--execute', action='store_true', help='Actually perform the reset (default is dry run)')
    return parser.parse_args()


def get_timezone(tz_name):
    """Get timezone object from name"""
    tz_map = {
        'PDT': 'America/Los_Angeles',
        'PST': 'America/Los_Angeles', 
        'EDT': 'America/New_York',
        'EST': 'America/New_York',
        'UTC': 'UTC'
    }
    
    tz_name = tz_name.upper()
    if tz_name in tz_map:
        return pytz.timezone(tz_map[tz_name])
    else:
        # Try to use it directly
        return pytz.timezone(tz_name)


def reset_events_and_transcripts(username, start_date, end_date, timezone_name, execute=False):
    """
    Reset events and transcriptions for a user within a date range
    
    Args:
        username: Username to reset
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD) 
        timezone_name: Timezone name (e.g., 'PDT', 'UTC')
        execute: Whether to actually perform the reset
    """
    
    # Parse dates and timezone
    tz = get_timezone(timezone_name)
    start_dt = tz.localize(datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0))
    end_dt = tz.localize(datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
    
    # Convert to UTC for database queries
    start_utc = start_dt.astimezone(pytz.UTC)
    end_utc = end_dt.astimezone(pytz.UTC)
    
    print(f"🔍 Searching for {username} data from {start_date} to {end_date} ({timezone_name})")
    print(f"   UTC range: {start_utc} to {end_utc}")
    
    session = SessionLocal()
    
    try:
        # Find matching events
        all_events = session.query(EventDB).filter(EventDB.username == username).all()
        
        matching_events = []
        for event in all_events:
            event_time = event.created_at.replace(tzinfo=pytz.UTC) if event.created_at.tzinfo is None else event.created_at
            if start_utc <= event_time <= end_utc:
                matching_events.append(event)
        
        # Find matching transcriptions
        all_transcriptions = session.query(TranscriptionResultDB).filter(TranscriptionResultDB.username == username).all()
        
        matching_transcriptions = []
        for t in all_transcriptions:
            t_time = t.start_time.replace(tzinfo=pytz.UTC) if t.start_time.tzinfo is None else t.start_time
            if start_utc <= t_time <= end_utc:
                matching_transcriptions.append(t)
        
        # Show summary
        print(f"\n📊 Found:")
        print(f"   - {len(matching_events)} events to delete")
        print(f"   - {len(matching_transcriptions)} transcriptions to reset")
        
        if len(matching_events) > 0:
            print(f"\n📝 Sample events (first 5):")
            for i, event in enumerate(matching_events[:5]):
                print(f"   {i+1}. {event.event_title[:40]:<40} | mood={event.mood_score:2d}, stress={event.stress_level:2d}, energy={event.energy_level:2d}")
        
        if len(matching_transcriptions) > 0:
            # Count transcription statuses
            status_counts = {}
            for t in matching_transcriptions:
                status = t.analysis_status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"\n📈 Transcription status breakdown:")
            for status, count in status_counts.items():
                print(f"   - {status}: {count}")
        
        if not execute:
            print(f"\n🔍 DRY RUN MODE - Nothing was changed")
            print(f"   Add --execute to actually perform the reset")
            return
        
        # Perform the reset
        print(f"\n🗑️  Deleting {len(matching_events)} events...")
        for event in matching_events:
            session.delete(event)
        
        print(f"🔄 Resetting transcriptions to pending...")
        reset_count = 0
        for t in matching_transcriptions:
            if t.analysis_status in ['completed', 'failed']:
                t.analysis_status = 'pending'
                t.analyzed_at = None
                reset_count += 1
        
        # Commit changes
        session.commit()
        
        print(f"\n✅ RESET COMPLETE!")
        print(f"   - Deleted: {len(matching_events)} events")
        print(f"   - Reset: {reset_count} transcriptions to pending")
        print(f"\n💡 Next steps:")
        print(f"   1. Trigger analyzer: curl -X POST 'http://localhost:8200/transcription-processor/trigger'")
        print(f"   2. Check results after processing completes")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


def main():
    args = parse_args()
    
    print(f"🚀 Event and Transcription Reset Tool")
    print(f"   Username: {args.username}")
    print(f"   Date range: {args.start_date} to {args.end_date}")
    print(f"   Timezone: {args.timezone}")
    print(f"   Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    
    reset_events_and_transcripts(
        username=args.username,
        start_date=args.start_date, 
        end_date=args.end_date,
        timezone_name=args.timezone,
        execute=args.execute
    )


if __name__ == "__main__":
    main()