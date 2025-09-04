#!/usr/bin/env python
"""
Migration script to:
1. Drop the old journal_files table
2. Create new events and daily_reflections tables
3. No data migration needed - we'll regenerate events fresh
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from nirva_service.db.pgsql_client import SessionLocal, engine
from nirva_service.db.pgsql_object import Base, EventDB, DailyReflectionDB
from loguru import logger


def drop_old_tables():
    """Drop the old journal_files table."""
    db = SessionLocal()
    try:
        logger.info("Dropping old journal_files table...")
        db.execute(text("DROP TABLE IF EXISTS journal_files CASCADE"))
        db.commit()
        logger.info("Successfully dropped journal_files table")
    except Exception as e:
        logger.error(f"Error dropping table: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_new_tables():
    """Create new events and daily_reflections tables."""
    try:
        logger.info("Creating new tables...")
        
        # Create only the new tables
        # This will create events and daily_reflections tables
        EventDB.__table__.create(engine, checkfirst=True)
        DailyReflectionDB.__table__.create(engine, checkfirst=True)
        
        logger.info("Successfully created events and daily_reflections tables")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise


def verify_migration():
    """Verify the migration was successful."""
    db = SessionLocal()
    try:
        # Check that new tables exist
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('events', 'daily_reflections', 'journal_files')
        """))
        
        tables = [row[0] for row in result]
        
        logger.info(f"Found tables: {tables}")
        
        if 'journal_files' in tables:
            logger.warning("Old journal_files table still exists!")
            return False
            
        if 'events' not in tables:
            logger.error("New events table not created!")
            return False
            
        if 'daily_reflections' not in tables:
            logger.error("New daily_reflections table not created!")
            return False
            
        logger.info("Migration verified successfully!")
        return True
        
    finally:
        db.close()


def main():
    """Run the migration."""
    logger.info("Starting migration to events table structure...")
    
    try:
        # Step 1: Drop old tables
        drop_old_tables()
        
        # Step 2: Create new tables
        create_new_tables()
        
        # Step 3: Verify
        if verify_migration():
            logger.info("✅ Migration completed successfully!")
            logger.info("Note: You'll need to reprocess transcriptions to generate new events")
        else:
            logger.error("❌ Migration verification failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()