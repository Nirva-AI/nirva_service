#!/usr/bin/env python3
"""
Script to add the missing captured_at column to the AWS database.
This ensures the production database schema matches the model definition.
"""

import os
import sys
from pathlib import Path

# Add src to path so we can import nirva modules
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root / 'src'))

def add_captured_at_column():
    """Add the captured_at column to the audio_files table on AWS."""

    print("🔧 Adding captured_at column to AWS database...")

    # Import here after path is set
    from nirva_service.db.pgsql_client import engine
    import sqlalchemy as sa

    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(sa.text('''
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'audio_files' AND column_name = 'captured_at'
            '''))

            if result.fetchone():
                print('✅ captured_at column already exists on AWS')
                return True

            print('📝 Adding captured_at column to audio_files table...')

            # Add the column
            conn.execute(sa.text('''
                ALTER TABLE audio_files
                ADD COLUMN captured_at TIMESTAMP WITH TIME ZONE
            '''))

            # Create index on the new column
            conn.execute(sa.text('''
                CREATE INDEX ix_audio_files_captured_at
                ON audio_files (captured_at)
            '''))

            conn.commit()
            print('✅ captured_at column added successfully with index')

            # Verify the addition
            result = conn.execute(sa.text('''
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'audio_files' AND column_name = 'captured_at'
            '''))

            row = result.fetchone()
            if row:
                print(f'✅ Verification: {row.column_name} ({row.data_type}, nullable: {row.is_nullable})')
                return True
            else:
                print('❌ Verification failed: captured_at column not found after creation')
                return False

    except Exception as e:
        print(f'❌ Error adding captured_at column: {e}')
        return False

if __name__ == "__main__":
    print("🚀 AWS Database Schema Update Script")
    print("📋 Adding captured_at column to audio_files table")
    print()

    success = add_captured_at_column()

    if success:
        print()
        print("🎉 AWS database schema update completed successfully!")
        print("📊 The captured_at column is now available for enhanced diarization.")
    else:
        print()
        print("💥 AWS database schema update failed!")
        print("⚠️ Please check the error messages above and try again.")
        sys.exit(1)