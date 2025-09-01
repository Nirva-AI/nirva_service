#!/bin/bash
# Migration script for adding analysis tracking to transcription_results table

set -e

echo "🔄 Running analysis tracking migration..."

# Check if we're on EC2 or local
if [ -f /etc/system-release ] && grep -q "Amazon Linux" /etc/system-release; then
    echo "Running on EC2, applying migration directly..."
    
    # Apply migration using psql
    psql -U postgres -d nirva << 'SQL'
-- Add analysis tracking columns
ALTER TABLE transcription_results 
ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20) DEFAULT 'pending';

ALTER TABLE transcription_results 
ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP WITH TIME ZONE;

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_analysis_status 
ON transcription_results(analysis_status, username, start_time);

-- Create index for date-based queries
CREATE INDEX IF NOT EXISTS idx_transcription_date 
ON transcription_results(DATE(start_time), username);

-- Show results
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'transcription_results' 
AND column_name IN ('analysis_status', 'analyzed_at');

SELECT indexname FROM pg_indexes 
WHERE tablename = 'transcription_results' 
AND indexname LIKE 'idx_%';
SQL
    
    echo "✅ EC2 migration complete!"
    exit 0
fi

# For local environment, use Python with environment variables
echo "Running locally, using Python migration..."

# Activate conda environment
source ~/miniconda3/bin/activate nirva 2>/dev/null || source ~/anaconda3/bin/activate nirva

# Run Python migration
python << 'EOF'
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Database connection from environment
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'nirva')

# Build connection URL
if DB_PASSWORD:
    DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
else:
    DB_URL = f'postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

print(f"Connecting to database at {DB_HOST}:{DB_PORT}/{DB_NAME}...")
engine = create_engine(DB_URL)

# Migration queries
migrations = [
    {
        'name': 'Add analysis_status column',
        'sql': """
            ALTER TABLE transcription_results 
            ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20) DEFAULT 'pending';
        """
    },
    {
        'name': 'Add analyzed_at column',
        'sql': """
            ALTER TABLE transcription_results 
            ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP WITH TIME ZONE;
        """
    },
    {
        'name': 'Create analysis_status index',
        'sql': """
            CREATE INDEX IF NOT EXISTS idx_analysis_status 
            ON transcription_results(analysis_status, username, start_time);
        """
    },
    {
        'name': 'Create date index',
        'sql': """
            CREATE INDEX IF NOT EXISTS idx_transcription_date 
            ON transcription_results(DATE(start_time), username);
        """
    }
]

# Run migrations
with engine.connect() as conn:
    for migration in migrations:
        try:
            print(f"Running: {migration['name']}")
            conn.execute(text(migration['sql']))
            conn.commit()
            print(f"✅ {migration['name']} - completed")
        except ProgrammingError as e:
            if 'already exists' in str(e):
                print(f"ℹ️  {migration['name']} - already exists")
            else:
                print(f"❌ {migration['name']} - error: {e}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ {migration['name']} - unexpected error: {e}")
            sys.exit(1)
    
    # Verify the migration
    print("\n📊 Verifying migration...")
    
    # Check columns
    result = conn.execute(text("""
        SELECT column_name, data_type, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'transcription_results' 
        AND column_name IN ('analysis_status', 'analyzed_at')
        ORDER BY column_name;
    """))
    
    print("\nNew columns:")
    for row in result:
        print(f"  - {row[0]}: {row[1]} (default: {row[2]})")
    
    # Check indexes
    result = conn.execute(text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'transcription_results' 
        AND indexname LIKE 'idx_%'
        ORDER BY indexname;
    """))
    
    print("\nIndexes:")
    for row in result:
        print(f"  - {row[0]}")

print("\n✅ All migrations completed successfully!")
EOF

echo "✅ Migration complete!"