#!/bin/bash
# Simple migration runner that handles common issues

set -e

echo "🗄️ Running database migrations..."

# Try to run as postgres user first (for EC2)
if [ -f /etc/system-release ] && grep -q "Amazon Linux" /etc/system-release; then
    echo "Running on EC2, using postgres user..."
    sudo -u postgres psql nirva << 'SQL'
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS detected_language VARCHAR(10);
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS sentiment_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS topics_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS intents_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS raw_response JSON;
SQL
    echo "✅ Migration complete!"
    exit 0
fi

# For other environments, try Python approach
# Activate conda environment
source ~/miniconda3/bin/activate nirva 2>/dev/null || source ~/anaconda3/bin/activate nirva

# Change to project directory
cd ~/nirva_service 2>/dev/null || cd .

# Create a Python script to run migrations safely
python << 'EOF'
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Database connection - use environment variables
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'nirva')

# Build connection URL from environment
if DB_PASSWORD:
    DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
else:
    DB_URL = f'postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

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