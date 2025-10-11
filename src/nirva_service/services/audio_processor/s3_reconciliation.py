"""
S3 Reconciliation Service

Periodically scans S3 for audio files that don't have corresponding database records.
This handles cases where S3 event notifications are lost or delayed.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Set
import boto3
from loguru import logger
from sqlalchemy.orm import Session

from nirva_service.db.pgsql_client import SessionLocal
from nirva_service.db.pgsql_object import AudioFileDB


class S3ReconciliationService:
    """Service to reconcile S3 files with database records."""

    def __init__(self, bucket_name: str, prefix: str = "native-audio/"):
        """
        Initialize the reconciliation service.

        Args:
            bucket_name: S3 bucket name to scan
            prefix: S3 prefix to filter files (default: native-audio/)
        """
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3_client = boto3.client('s3')

    async def find_unprocessed_files(self,
                                    max_age_hours: int = 24,
                                    limit: int = 100) -> List[dict]:
        """
        Find S3 files that don't have corresponding database records.

        Args:
            max_age_hours: Only check files uploaded within this many hours
            limit: Maximum number of unprocessed files to return

        Returns:
            List of S3 file information dictionaries
        """
        logger.info(f"[S3_RECONCILE] Scanning S3 bucket {self.bucket_name}/{self.prefix} for unprocessed files")

        # Get cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # List S3 objects
        unprocessed_files = []
        continuation_token = None

        while len(unprocessed_files) < limit:
            try:
                # Build request parameters
                list_params = {
                    'Bucket': self.bucket_name,
                    'Prefix': self.prefix,
                    'MaxKeys': 1000
                }
                if continuation_token:
                    list_params['ContinuationToken'] = continuation_token

                # List objects
                response = self.s3_client.list_objects_v2(**list_params)

                if 'Contents' not in response:
                    logger.info(f"[S3_RECONCILE] No objects found in {self.bucket_name}/{self.prefix}")
                    break

                # Check each object
                db: Session = SessionLocal()
                try:
                    for obj in response['Contents']:
                        # Skip if too old
                        if obj['LastModified'] < cutoff_time:
                            continue

                        # Skip if not a WAV file
                        if not obj['Key'].endswith('.wav'):
                            continue

                        # Check if exists in database
                        existing = db.query(AudioFileDB).filter_by(
                            s3_bucket=self.bucket_name,
                            s3_key=obj['Key']
                        ).first()

                        if not existing:
                            logger.warning(f"[S3_RECONCILE] Found unprocessed file: {obj['Key']}")
                            unprocessed_files.append({
                                'bucket': self.bucket_name,
                                'key': obj['Key'],
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'],
                                'event_name': 'ObjectCreated:Put',  # Simulate S3 event
                                'event_time': obj['LastModified'].isoformat()
                            })

                            if len(unprocessed_files) >= limit:
                                break

                finally:
                    db.close()

                # Check if there are more objects
                if not response.get('IsTruncated'):
                    break

                continuation_token = response.get('NextContinuationToken')

            except Exception as e:
                logger.error(f"[S3_RECONCILE] Error scanning S3: {e}")
                break

        logger.info(f"[S3_RECONCILE] Found {len(unprocessed_files)} unprocessed files")
        return unprocessed_files

    async def get_known_s3_keys(self, prefix: str, max_age_hours: int = 24) -> Set[str]:
        """
        Get all S3 keys that are already in the database.

        Args:
            prefix: S3 prefix to filter
            max_age_hours: Only check recent files

        Returns:
            Set of S3 keys that exist in database
        """
        db: Session = SessionLocal()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

            # Query database for recent files
            records = db.query(AudioFileDB.s3_key).filter(
                AudioFileDB.s3_bucket == self.bucket_name,
                AudioFileDB.s3_key.like(f"{prefix}%"),
                AudioFileDB.created_at >= cutoff_time
            ).all()

            return {record.s3_key for record in records}

        finally:
            db.close()


async def reconciliation_task(bucket_name: str, process_callback, interval_seconds: int = 300):
    """
    Background task that periodically checks for unprocessed S3 files.

    Args:
        bucket_name: S3 bucket to scan
        process_callback: Async function to process found files
        interval_seconds: How often to run reconciliation (default: 5 minutes)
    """
    service = S3ReconciliationService(bucket_name)

    logger.info(f"[S3_RECONCILE] Starting reconciliation task, checking every {interval_seconds}s")

    while True:
        try:
            # Find unprocessed files
            unprocessed = await service.find_unprocessed_files(
                max_age_hours=24,  # Check files from last 24 hours
                limit=50  # Process up to 50 files at a time
            )

            if unprocessed:
                logger.info(f"[S3_RECONCILE] Processing {len(unprocessed)} missing files")

                # Process each file
                for file_info in unprocessed:
                    try:
                        # Call the processing callback (same as S3 event processing)
                        await process_callback(file_info)
                        logger.info(f"[S3_RECONCILE] Successfully processed {file_info['key']}")
                    except Exception as e:
                        logger.error(f"[S3_RECONCILE] Failed to process {file_info['key']}: {e}")

            # Wait before next check
            await asyncio.sleep(interval_seconds)

        except Exception as e:
            logger.error(f"[S3_RECONCILE] Error in reconciliation task: {e}")
            await asyncio.sleep(interval_seconds)