#!/usr/bin/env python3
"""Run database migration to add Deepgram fields."""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.audio_processor')

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:nirva2025@localhost:5432/nirva')

def run_migration():
    """Add new columns for Deepgram fields."""
    engine = create_engine(DATABASE_URL)
    
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
                result = conn.execute(text(f"""
                    ALTER TABLE transcription_results 
                    ADD COLUMN {column_name} {column_type}
                """))
                conn.commit()
                print(f"✅ Added column: {column_name}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"ℹ️  Column {column_name} already exists")
                else:
                    print(f"❌ Error adding column {column_name}: {e}")
                conn.rollback()
        
        print("\n✅ Migration completed!")

if __name__ == "__main__":
    run_migration()