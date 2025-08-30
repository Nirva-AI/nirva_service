#!/usr/bin/env python3
"""Run database migration to add Deepgram fields."""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from sqlalchemy import text
from nirva_service.db.database import get_sync_db_engine

def run_migration():
    """Add new columns for Deepgram fields."""
    engine = get_sync_db_engine()
    
    with engine.connect() as conn:
        # Add columns one by one to handle if they already exist
        columns = [
            ("detected_language", "VARCHAR(10)"),
            ("sentiment_data", "JSON"),
            ("topics_data", "JSON"),
            ("intents_data", "JSON"),
            ("raw_response", "JSON")
        ]
        
        for column_name, column_type in columns:
            try:
                conn.execute(text(f"""
                    ALTER TABLE transcription_results 
                    ADD COLUMN {column_name} {column_type}
                """))
                conn.commit()
                print(f"✅ Added column: {column_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️  Column {column_name} already exists")
                else:
                    print(f"❌ Error adding column {column_name}: {e}")
                conn.rollback()
        
        print("\n✅ Migration completed!")

if __name__ == "__main__":
    run_migration()