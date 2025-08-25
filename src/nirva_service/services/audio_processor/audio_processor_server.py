"""
Audio Processor Server - Polls SQS for S3 upload events and processes audio files.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime
import json

from fastapi import FastAPI, HTTPException
from loguru import logger
import boto3
from sqlalchemy.orm import Session

from nirva_service.services.storage.sqs_service import get_sqs_service
from nirva_service.db.pgsql_client import SessionLocal
from nirva_service.db.pgsql_object import AudioFileDB
from nirva_service.config.configuration import AudioProcessorServerConfig


# Configuration
config = AudioProcessorServerConfig()

# Background task reference
background_task = None


async def process_sqs_messages():
    """
    Background task that continuously polls SQS for messages.
    """
    sqs_service = get_sqs_service()
    s3_client = boto3.client(
        's3',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    logger.info("Starting SQS polling background task...")
    
    while True:
        try:
            # Poll for messages
            messages = sqs_service.poll_messages(
                max_messages=config.max_messages_per_poll,
                wait_time_seconds=20,  # Long polling
                visibility_timeout=config.visibility_timeout
            )
            
            if messages:
                logger.info(f"Processing {len(messages)} messages from SQS")
                
                for message in messages:
                    try:
                        # Process S3 event messages
                        if 'bucket' in message and 'key' in message:
                            await process_s3_event(message, s3_client)
                            
                            # Delete message after successful processing
                            sqs_service.delete_message(message['receipt_handle'])
                        else:
                            logger.warning(f"Non-S3 message received: {message.get('message_id')}")
                            # Still delete non-S3 messages to prevent reprocessing
                            sqs_service.delete_message(message['receipt_handle'])
                            
                    except Exception as e:
                        logger.error(f"Error processing message {message.get('message_id')}: {e}")
                        # Message will become visible again after visibility timeout
            
            # Small delay between polls if no messages
            if not messages:
                await asyncio.sleep(config.poll_interval_seconds)
                
        except Exception as e:
            logger.error(f"Error in SQS polling loop: {e}")
            await asyncio.sleep(10)  # Wait before retrying


async def process_s3_event(message: dict, s3_client) -> None:
    """
    Process an S3 event notification.
    
    Args:
        message: Parsed SQS message containing S3 event information
        s3_client: Boto3 S3 client
    """
    bucket = message['bucket']
    key = message['key']
    event_name = message['event_name']
    
    logger.info(f"Processing S3 event: {event_name} for s3://{bucket}/{key}")
    
    # Only process ObjectCreated events
    if not event_name.startswith('ObjectCreated'):
        logger.info(f"Ignoring event type: {event_name}")
        return
    
    # Extract user information from the S3 key
    # Expected format: native-audio/{encoded_user_id}/segment_*.wav
    key_parts = key.split('/')
    if len(key_parts) < 3 or key_parts[0] != 'native-audio':
        logger.warning(f"Unexpected S3 key format: {key}")
        return
    
    # The second part is likely a JWT token or encoded user identifier
    # This appears to be part of a JWT token (starts with eyJhbGci which decodes to {"alg")
    encoded_user_id = key_parts[1]
    filename = key_parts[2]
    
    # For now, use a hash of the encoded ID as a consistent user identifier
    # This ensures we can track files from the same user session
    import hashlib
    user_id_hash = hashlib.sha256(encoded_user_id.encode()).hexdigest()[:12]
    
    # Use the hash for database storage (keeps it consistent and shorter)
    user_id = user_id_hash
    
    logger.info(f"Processing audio file: {filename} for user session: {user_id}")
    
    # Get file metadata from S3
    try:
        head_response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = head_response.get('ContentLength', 0)
        content_type = head_response.get('ContentType', '')
        
        # Determine file format from content type or extension
        file_format = None
        if 'audio' in content_type:
            file_format = content_type.split('/')[-1]
        elif '.' in key:
            file_format = key.split('.')[-1].lower()
        
        logger.info(f"File metadata - Size: {file_size}, Type: {content_type}, Format: {file_format}")
        
    except Exception as e:
        logger.error(f"Error getting S3 object metadata: {e}")
        file_size = message.get('size', 0)
        file_format = None
    
    # Store in database
    db: Session = SessionLocal()
    try:
        # Check if file already exists in database
        existing_file = db.query(AudioFileDB).filter_by(
            s3_bucket=bucket,
            s3_key=key
        ).first()
        
        if existing_file:
            logger.info(f"File already tracked in database: {existing_file.id}")
        else:
            # Create new audio file record
            audio_file = AudioFileDB(
                user_id=None,  # No direct user mapping for native-audio uploads
                username=user_id,  # Using the hash as session identifier
                s3_bucket=bucket,
                s3_key=key,
                file_size=file_size,
                format=file_format,
                status="uploaded",
                uploaded_at=datetime.fromisoformat(message['event_time'].replace('Z', '+00:00'))
            )
            
            db.add(audio_file)
            db.commit()
            db.refresh(audio_file)
            
            logger.info(f"Created audio file record: {audio_file.id} for s3://{bucket}/{key}")
            
            # TODO: Queue for transcription processing
            # For now, just log that it's ready for processing
            logger.info(f"Audio file {audio_file.id} ready for transcription")
    
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle - start/stop background tasks."""
    global background_task
    
    # Check if SQS queue URL is configured
    sqs_queue_url = os.getenv('SQS_QUEUE_URL', '')
    if not sqs_queue_url:
        logger.warning("SQS_QUEUE_URL not configured. SQS polling will not start.")
        logger.warning("Set SQS_QUEUE_URL environment variable to enable S3 event processing.")
    else:
        logger.info(f"SQS Queue URL configured: {sqs_queue_url[:50]}...")
        # Start background task for SQS polling
        background_task = asyncio.create_task(process_sqs_messages())
        logger.info("Started SQS polling background task")
    
    yield
    
    # Cleanup
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("SQS polling background task cancelled")


# Initialize FastAPI app
app = FastAPI(
    title=config.fast_api_title,
    version=config.fast_api_version,
    description=config.fast_api_description,
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint."""
    sqs_configured = bool(os.getenv('SQS_QUEUE_URL'))
    return {
        "service": "Audio Processor",
        "status": "running",
        "sqs_polling": "enabled" if sqs_configured else "disabled",
        "port": config.port
    }


@app.get("/status")
async def get_status():
    """Get detailed service status."""
    db: Session = SessionLocal()
    try:
        # Get audio file statistics
        total_files = db.query(AudioFileDB).count()
        uploaded_files = db.query(AudioFileDB).filter_by(status="uploaded").count()
        processing_files = db.query(AudioFileDB).filter_by(status="processing").count()
        transcribed_files = db.query(AudioFileDB).filter_by(status="transcribed").count()
        failed_files = db.query(AudioFileDB).filter_by(status="failed").count()
        
        return {
            "service": "Audio Processor",
            "sqs_configured": bool(os.getenv('SQS_QUEUE_URL')),
            "database_stats": {
                "total_files": total_files,
                "uploaded": uploaded_files,
                "processing": processing_files,
                "transcribed": transcribed_files,
                "failed": failed_files
            }
        }
    finally:
        db.close()


@app.post("/test/send-sqs-message")
async def test_send_message(bucket: str = "test-bucket", key: str = "test-key"):
    """Send a test message to SQS (for testing)."""
    sqs_service = get_sqs_service()
    
    # Create a fake S3 event message
    test_message = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "eventTime": datetime.utcnow().isoformat() + "Z",
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key, "size": 1024}
                }
            }
        ]
    }
    
    message_id = sqs_service.send_message(test_message)
    if message_id:
        return {"message": "Test message sent", "message_id": message_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test message")