#!/bin/bash
# Simple migration runner that handles common issues

set -e

echo "🗄️ Running database migrations..."

# Activate conda environment
source ~/miniconda3/bin/activate nirva

# Change to project directory
cd ~/nirva_service

# Create a Python script to run migrations safely
python << 'EOF'
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Database connection
DB_URL = os.getenv('DATABASE_URL', 'postgresql://nirva:nirva2025@localhost/nirva')

print("Connecting to database...")
engine = create_engine(DB_URL)

# Define the migrations
migrations = [
    {
        'name': 'Add Deepgram fields',
        'sql': """
            ALTER TABLE transcription_results 
            ADD COLUMN IF NOT EXISTS detected_language VARCHAR(10);
            
            ALTER TABLE transcription_results 
            ADD COLUMN IF NOT EXISTS sentiment_data JSON;
            
            ALTER TABLE transcription_results 
            ADD COLUMN IF NOT EXISTS topics_data JSON;
            
            ALTER TABLE transcription_results 
            ADD COLUMN IF NOT EXISTS intents_data JSON;
            
            ALTER TABLE transcription_results 
            ADD COLUMN IF NOT EXISTS raw_response JSON;
        """
    }
]

# Run migrations
with engine.connect() as conn:
    for migration in migrations:
        try:
            print(f"Running migration: {migration['name']}")
            statements = [s.strip() for s in migration['sql'].split(';') if s.strip()]
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()
            print(f"✅ {migration['name']} - completed")
        except ProgrammingError as e:
            if 'already exists' in str(e):
                print(f"ℹ️  {migration['name']} - already applied")
            else:
                print(f"❌ {migration['name']} - error: {e}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ {migration['name']} - unexpected error: {e}")
            sys.exit(1)

print("\n✅ All migrations completed successfully!")
EOF

echo "✅ Migration complete!"