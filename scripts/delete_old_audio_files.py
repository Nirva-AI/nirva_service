#!/usr/bin/env python3
"""
Safe S3 Audio File Deletion Script

Deletes audio files from S3 and database for files uploaded before a specified date.
This script includes multiple safety measures and batch processing.

Usage:
    python scripts/delete_old_audio_files.py --before-date 2025-10-01 --dry-run
    python scripts/delete_old_audio_files.py --before-date 2025-10-01 --execute --batch-size 100
"""

import argparse
import os
import sys
from datetime import datetime
from typing import List, Tuple
import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pathlib import Path


def load_environment():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / '.env'
    if not env_file.exists():
        raise FileNotFoundError(f".env file not found at {env_file}")

    with open(env_file, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value


def get_s3_client():
    """Create S3 client with credentials from environment"""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )


def get_database_engine():
    """Create database engine"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")
    return create_engine(db_url)


def analyze_files_to_delete(engine, before_date: str) -> Tuple[int, List[str]]:
    """Analyze files that would be deleted"""
    print(f"\n=== ANALYSIS: Files to delete before {before_date} ===")

    with engine.connect() as conn:
        # Count total files to delete
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM audio_files
            WHERE uploaded_at < :before_date
        """), {"before_date": before_date})
        total_count = result.scalar()

        # Get breakdown by month
        result = conn.execute(text("""
            SELECT
                DATE_TRUNC('month', uploaded_at) as month,
                COUNT(*) as count
            FROM audio_files
            WHERE uploaded_at < :before_date
            GROUP BY DATE_TRUNC('month', uploaded_at)
            ORDER BY month
        """), {"before_date": before_date})

        print(f"Total files to delete: {total_count:,}")
        print("Breakdown by month:")
        for row in result:
            print(f"  {row.month.strftime('%Y-%m')}: {row.count:,} files")

        # Get sample S3 keys for verification
        result = conn.execute(text("""
            SELECT s3_bucket, s3_key, username, uploaded_at
            FROM audio_files
            WHERE uploaded_at < :before_date
            ORDER BY uploaded_at
            LIMIT 10
        """), {"before_date": before_date})

        sample_keys = []
        print(f"\nSample files to delete:")
        for row in result:
            print(f"  s3://{row.s3_bucket}/{row.s3_key} ({row.uploaded_at}) - {row.username}")
            sample_keys.append(row.s3_key)

        return total_count, sample_keys


def delete_files_batch(engine, s3_client, bucket_name: str, before_date: str, batch_size: int, dry_run: bool = True) -> Tuple[int, int]:
    """Delete files in batches with proper error handling"""

    Session = sessionmaker(bind=engine)
    deleted_s3_count = 0
    deleted_db_count = 0
    failed_count = 0

    print(f"\n=== {'DRY RUN' if dry_run else 'EXECUTION'}: Deleting files in batches of {batch_size} ===")

    with Session() as session:
        # Get total count for progress tracking
        total_result = session.execute(text("""
            SELECT COUNT(*) FROM audio_files WHERE uploaded_at < :before_date
        """), {"before_date": before_date})
        total_files = total_result.scalar()

        processed = 0

        while True:
            # Get next batch of files
            batch_result = session.execute(text("""
                SELECT id, s3_bucket, s3_key, username, uploaded_at
                FROM audio_files
                WHERE uploaded_at < :before_date
                ORDER BY uploaded_at
                LIMIT :batch_size
            """), {"before_date": before_date, "batch_size": batch_size})

            batch = batch_result.fetchall()
            if not batch:
                break

            print(f"Processing batch: {processed + 1} to {processed + len(batch)} of {total_files}")

            # Process each file in the batch
            for row in batch:
                file_id, s3_bucket, s3_key, username, uploaded_at = row

                try:
                    if not dry_run:
                        # Delete from S3
                        s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)
                        deleted_s3_count += 1

                        # Delete from database
                        session.execute(text("""
                            DELETE FROM audio_files WHERE id = :file_id
                        """), {"file_id": file_id})
                        deleted_db_count += 1

                    processed += 1

                    if processed % 50 == 0:  # Progress update every 50 files
                        print(f"  Processed {processed:,} files...")
                        if not dry_run:
                            session.commit()  # Commit periodically

                except Exception as e:
                    print(f"  ERROR processing s3://{s3_bucket}/{s3_key}: {e}")
                    failed_count += 1
                    if not dry_run:
                        session.rollback()

            if dry_run:
                break  # Don't loop in dry run mode

        if not dry_run:
            session.commit()  # Final commit

    return deleted_s3_count if not dry_run else processed, deleted_db_count, failed_count


def main():
    parser = argparse.ArgumentParser(description='Delete old audio files from S3 and database')
    parser.add_argument('--before-date', required=True, help='Delete files before this date (YYYY-MM-DD)')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of files to process per batch')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--execute', action='store_true', help='Actually perform the deletion')

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("ERROR: Must specify either --dry-run or --execute")
        sys.exit(1)

    if args.dry_run and args.execute:
        print("ERROR: Cannot specify both --dry-run and --execute")
        sys.exit(1)

    # Validate date format
    try:
        datetime.strptime(args.before_date, '%Y-%m-%d')
    except ValueError:
        print("ERROR: Date must be in YYYY-MM-DD format")
        sys.exit(1)

    print(f"Audio File Deletion Script")
    print(f"Date threshold: {args.before_date}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print(f"Batch size: {args.batch_size}")

    try:
        # Load environment and setup connections
        load_environment()
        engine = get_database_engine()
        s3_client = get_s3_client()
        bucket_name = os.getenv('AWS_S3_BUCKET')

        if not bucket_name:
            raise ValueError("AWS_S3_BUCKET not found in environment")

        print(f"S3 Bucket: {bucket_name}")

        # Analyze what would be deleted
        total_count, sample_keys = analyze_files_to_delete(engine, args.before_date)

        if total_count == 0:
            print("No files found to delete.")
            return

        # Confirmation for actual deletion
        if args.execute:
            print(f"\n⚠️  WARNING: This will permanently delete {total_count:,} files from S3 and database!")
            print("This action cannot be undone.")
            confirmation = input("Type 'DELETE' to confirm: ")
            if confirmation != 'DELETE':
                print("Deletion cancelled.")
                return

        # Perform deletion
        s3_deleted, db_deleted, failed = delete_files_batch(
            engine, s3_client, bucket_name, args.before_date, args.batch_size, args.dry_run
        )

        # Summary
        print(f"\n=== SUMMARY ===")
        if args.dry_run:
            print(f"Would delete: {s3_deleted:,} files")
        else:
            print(f"S3 files deleted: {s3_deleted:,}")
            print(f"Database records deleted: {db_deleted:,}")
            if failed > 0:
                print(f"Failed deletions: {failed:,}")

        print("Script completed successfully.")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()