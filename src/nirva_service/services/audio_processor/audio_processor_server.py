"""
Audio Processor Server - Polls SQS for S3 upload events and processes audio files.
"""

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
from datetime import datetime, timedelta, timezone
import json

from fastapi import FastAPI, HTTPException
from loguru import logger
import boto3
from sqlalchemy.orm import Session

from nirva_service.services.storage.sqs_service import get_sqs_service
from nirva_service.services.audio_processing import get_vad_service, get_deepgram_service
from nirva_service.services.audio_processing.enhanced_deepgram_service import get_enhanced_deepgram_service
from nirva_service.services.audio_processing.pyannote_service import get_pyannote_service
from nirva_service.services.audio_processing.diarization_merger import get_diarization_merger
from nirva_service.services.audio_processor.batch_manager import get_batch_manager
from nirva_service.services.audio_processor.s3_reconciliation import reconciliation_task
from nirva_service.db.pgsql_client import SessionLocal
from nirva_service.db.pgsql_object import AudioFileDB, AudioBatchDB, TranscriptionResultDB
from nirva_service.config.configuration import AudioProcessorServerConfig


# Configuration
config = AudioProcessorServerConfig()

# Background task reference
background_task = None


async def process_batch_transcription(batch_id: str) -> None:
    """
    Process a batch of audio segments for transcription.
    
    Args:
        batch_id: ID of the batch to process
    """
    logger.info(f"Starting transcription for batch {batch_id}")
    
    db: Session = SessionLocal()
    vad_service = get_vad_service()
    enhanced_deepgram_service = get_enhanced_deepgram_service()
    pyannote_service = get_pyannote_service()
    diarization_merger = get_diarization_merger()
    s3_client = boto3.client('s3')
    batch_manager = get_batch_manager()
    
    try:
        # Get batch and its segments
        batch = db.query(AudioBatchDB).filter_by(id=batch_id).first()
        if not batch:
            logger.error(f"Batch {batch_id} not found")
            return
        
        # Mark as processing
        batch_manager.mark_batch_processing(batch, db)
        
        # Get all segments in the batch
        segments = batch_manager.get_batch_segments(batch, db)
        
        if not segments:
            logger.warning(f"No segments found for batch {batch_id}")
            batch_manager.mark_batch_completed(batch, db)
            return
        
        logger.info(f"Processing {len(segments)} segments for batch {batch_id}")
        
        # Download audio files and get VAD results
        audio_files_with_vad = []
        temp_files = []
        
        for segment in segments:
            try:
                # Download audio from S3
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                    temp_path = tmp_file.name
                    temp_files.append(temp_path)
                
                s3_client.download_file(segment.s3_bucket, segment.s3_key, temp_path)
                
                # Parse VAD results
                vad_result = {
                    'segments': json.loads(segment.speech_segments) if segment.speech_segments else [],
                    'speech_duration': segment.total_speech_duration or 0
                }
                
                audio_files_with_vad.append((temp_path, vad_result))
                
            except Exception as e:
                logger.error(f"Error downloading segment {segment.id}: {e}")
                continue
        
        if not audio_files_with_vad:
            logger.error(f"No audio files could be downloaded for batch {batch_id}")
            batch_manager.mark_batch_completed(batch, db)
            return
        
        # Extract and concatenate speech segments
        logger.info(f"Extracting speech from {len(audio_files_with_vad)} files")
        speech_audio = vad_service.extract_and_concat_speech(audio_files_with_vad)
        
        if not speech_audio:
            logger.warning(f"No speech extracted from batch {batch_id}")
            batch_manager.mark_batch_completed(batch, db)
            return
        
        # Dual API Approach: Deepgram for word-level transcription + Pyannote for diarization
        logger.info(f"Starting dual API processing for {len(speech_audio)} bytes")

        # Determine S3 URL for pyannote.ai processing
        temp_audio_file = None
        temp_s3_key = None

        # Ensure both services process the exact same audio
        # Always upload the VAD-processed speech_audio for consistent processing
        try:
            # Save VAD-processed audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_audio_file = temp_file.name
                temp_file.write(speech_audio)

            # Upload VAD-processed audio to S3 for pyannote.ai processing
            temp_s3_key = f"temp-diarization/{batch_id}.wav"
            s3_bucket = os.getenv('AWS_S3_BUCKET')
            s3_client.upload_file(temp_audio_file, s3_bucket, temp_s3_key)

            # Create presigned URL for pyannote.ai access (bucket is private)
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': s3_bucket, 'Key': temp_s3_key},
                ExpiresIn=3600  # 1 hour
            )

            logger.info(f"Uploaded VAD-processed audio to S3 for synchronized processing: {temp_s3_key}")

            # Step 1: Get word-level transcription from Enhanced Deepgram (no diarization)
            logger.info("Step 1: Getting word-level transcription from Deepgram (VAD-processed audio)")
            deepgram_result = await enhanced_deepgram_service.transcribe_audio_with_words(speech_audio)

            # Step 2: Get speaker diarization from Pyannote.ai (same VAD-processed audio)
            logger.info("Step 2: Getting speaker diarization from Pyannote.ai (same VAD-processed audio)")
            speaker_segments = await pyannote_service.diarize_audio_url(presigned_url)

            # Step 3: Merge diarization with word timestamps to create sentence-level output
            logger.info("Step 3: Merging diarization with word timestamps")
            base_time = batch.first_segment_time or datetime.now()
            merged_transcription = diarization_merger.merge_diarization_with_words(
                speaker_segments,
                deepgram_result.get('words', []),
                base_time
            )

            # Create combined result
            transcription_result = {
                'transcription': merged_transcription,
                'confidence': deepgram_result.get('confidence', 0.0),
                'language': deepgram_result.get('language', 'en'),
                'speaker_segments': speaker_segments,
                'word_count': len(deepgram_result.get('words', [])),
                'sentence_count': len([s for s in merged_transcription.split('[') if 'Speaker' in s]),
                'sentiment_data': deepgram_result.get('sentiment_data'),
                'topics_data': deepgram_result.get('topics_data'),
                'intents_data': deepgram_result.get('intents_data'),
                'raw_response': deepgram_result.get('raw_response')
            }

            logger.info(
                f"Dual API processing complete: {len(speaker_segments)} speakers, "
                f"{transcription_result['word_count']} words, "
                f"{transcription_result['sentence_count']} sentences"
            )

        except Exception as e:
            logger.error(f"Failed to process audio with dual API: {e}")
            raise
        finally:
            # Clean up temporary files
            if temp_audio_file and os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            # Clean up temporary S3 object
            if temp_s3_key:
                try:
                    s3_client.delete_object(Bucket=s3_bucket, Key=temp_s3_key)
                    logger.debug(f"Cleaned up temporary S3 object: {temp_s3_key}")
                except:
                    pass
        
        # Check if transcription text is meaningful (not null, not empty, more than 1 character)
        transcription_text = transcription_result.get('transcription', '')
        if not transcription_text or len(transcription_text.strip()) <= 1:
            logger.warning(
                f"Batch {batch_id}: Dropping empty/minimal transcription "
                f"(text: '{transcription_text}', length: {len(transcription_text.strip())})"
            )
            # Mark batch as completed but don't save the transcription
            batch_manager.mark_batch_completed(batch, db)
            
            # Update segment statuses to indicate they were processed but had no meaningful content
            for segment in segments:
                segment.status = 'transcribed'
                segment.processed_at = datetime.utcnow()
            db.commit()
            return
        
        # Calculate time range based on actual capture times
        first_segment = segments[0]
        last_segment = segments[-1]
        
        # Use captured_at if available, fallback to uploaded_at for backward compatibility
        start_time = first_segment.captured_at or first_segment.uploaded_at
        end_time_base = last_segment.captured_at or last_segment.uploaded_at
        end_time = end_time_base + timedelta(seconds=last_segment.duration_seconds or 30)
        
        logger.info(f"Transcription time range: {start_time} to {end_time} (using {'capture' if first_segment.captured_at else 'upload'} timestamps)")
        
        # Store transcription result with all new fields
        transcription = TranscriptionResultDB(
            username=batch.username,
            batch_id=batch_id,
            start_time=start_time,
            end_time=end_time,
            transcription_text=transcription_text,
            transcription_confidence=transcription_result['confidence'],
            transcription_service='deepgram+pyannote',
            detected_language=transcription_result.get('language'),
            sentiment_data=transcription_result.get('sentiment_data'),
            topics_data=transcription_result.get('topics_data'),
            intents_data=transcription_result.get('intents_data'),
            raw_response=transcription_result.get('raw_response'),
            num_segments=len(segments)
        )
        
        db.add(transcription)
        db.commit()
        
        # Update segment statuses
        for segment in segments:
            segment.status = 'transcribed'
            segment.processed_at = datetime.utcnow()
        
        # Mark batch as completed
        batch_manager.mark_batch_completed(batch, db)
        
        logger.info(
            f"Batch {batch_id} transcription complete: "
            f"{len(transcription_text)} chars, "
            f"confidence: {transcription_result['confidence']:.2f}"
        )
        
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {e}")
        try:
            batch = db.query(AudioBatchDB).filter_by(id=batch_id).first()
            if batch:
                batch.status = 'failed'
                db.commit()
        except:
            pass
    
    finally:
        # Clean up temp files
        if 'temp_files' in locals():
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        
        db.close()


async def batch_monitor_task():
    """
    Background task that monitors batches for timeout and triggers transcription.
    """
    batch_manager = get_batch_manager()
    
    logger.info("Starting batch monitor background task...")
    
    while True:
        try:
            db: Session = SessionLocal()
            
            try:
                # Get batches ready for processing (exceeded timeout)
                ready_batches = batch_manager.get_batches_ready_for_processing(db)
                
                for batch in ready_batches:
                    logger.info(f"Processing batch {batch.id} due to timeout")
                    asyncio.create_task(process_batch_transcription(str(batch.id)))
                
            finally:
                db.close()
            
            # Check every 10 seconds
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"Error in batch monitor task: {e}")
            await asyncio.sleep(10)


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

    poll_count = 0
    while True:
        poll_count += 1
        try:
            logger.debug(f"[SQS_POLL_{poll_count}] Starting poll for up to {config.max_messages_per_poll} messages...")

            # Poll for messages
            messages = sqs_service.poll_messages(
                max_messages=config.max_messages_per_poll,
                wait_time_seconds=20,  # Long polling
                visibility_timeout=config.visibility_timeout
            )

            if messages:
                logger.info(f"[SQS_POLL_{poll_count}] Received {len(messages)} messages from SQS")
                logger.info(f"[SQS_POLL_{poll_count}] Message keys: {[m.get('key', 'unknown') for m in messages]}")
                
                # Process all messages concurrently to prevent blocking
                async def process_single_message(idx: int, message: dict) -> tuple:
                    """Process a single SQS message and return result."""
                    try:
                        # Process S3 event messages
                        if 'bucket' in message and 'key' in message:
                            logger.info(f"[SQS_MSG_{idx}/{len(messages)}] Processing message for {message['key']}")

                            # Process the event and check if database record was created
                            success = await process_s3_event(message, s3_client)

                            if success:
                                # Only delete message after successful database record creation
                                sqs_service.delete_message(message['receipt_handle'])
                                logger.info(f"[SQS_MSG_{idx}/{len(messages)}] Successfully processed and deleted message for {message['key']}")
                            else:
                                logger.error(f"[SQS_MSG_{idx}/{len(messages)}] Failed to process S3 event for {message['key']}, keeping message in queue for retry")
                                # Message will become visible again after visibility timeout

                            return (message['key'], success)
                        else:
                            logger.warning(f"[SQS_MSG_{idx}/{len(messages)}] Non-S3 message received: {message.get('message_id')}")
                            # Still delete non-S3 messages to prevent reprocessing
                            sqs_service.delete_message(message['receipt_handle'])
                            return (message.get('message_id', 'unknown'), True)

                    except Exception as e:
                        logger.error(f"[SQS_MSG_{idx}/{len(messages)}] Error processing message {message.get('message_id')}: {e}")
                        logger.error(f"[SQS_MSG_{idx}/{len(messages)}] Failed to process {message.get('key', 'unknown')}, will retry after visibility timeout")
                        return (message.get('key', 'unknown'), False)

                # Process all messages concurrently
                logger.info(f"[SQS_POLL_{poll_count}] Processing {len(messages)} messages concurrently...")
                tasks = [process_single_message(idx, msg) for idx, msg in enumerate(messages, 1)]
                processing_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Log batch processing summary
                successful = sum(1 for r in processing_results if isinstance(r, tuple) and r[1])
                failed = len(processing_results) - successful
                logger.info(f"[SQS_POLL_{poll_count}] Batch complete: {successful} successful, {failed} failed")
                logger.info(f"[SQS_POLL_{poll_count}] Results: {processing_results}")
            
            # Small delay between polls if no messages
            if not messages:
                logger.debug(f"[SQS_POLL_{poll_count}] No messages received, sleeping {config.poll_interval_seconds}s")
                await asyncio.sleep(config.poll_interval_seconds)
            else:
                # Very short delay even after processing to allow new messages to arrive
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in SQS polling loop: {e}")
            await asyncio.sleep(10)  # Wait before retrying


async def apply_vad_processing(audio_file_id: str, bucket: str, key: str) -> None:
    """
    Apply Voice Activity Detection to an audio file and add to batch.
    
    Args:
        audio_file_id: Database ID of the audio file
        bucket: S3 bucket name
        key: S3 object key
    """
    logger.info(f"[VAD] Starting VAD processing for audio_file_id: {audio_file_id}, s3://{bucket}/{key}")
    
    # Initialize services
    s3_client = boto3.client('s3')
    vad_service = get_vad_service()
    batch_manager = get_batch_manager()
    db: Session = SessionLocal()
    
    try:
        # Download audio file from S3
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            temp_path = tmp_file.name
            
        logger.info(f"Downloading audio from s3://{bucket}/{key}")
        s3_client.download_file(bucket, key, temp_path)
        
        # Apply VAD
        logger.info(f"Applying VAD to {temp_path}")
        vad_result = vad_service.process_audio_file(
            temp_path,
            return_seconds=True,
            min_speech_duration_ms=250,  # Minimum 250ms speech
            min_silence_duration_ms=100,  # Minimum 100ms silence to split
            threshold=0.08,  # Ultra-sensitive to match client threshold
            speech_pad_ms=100  # Increased padding
        )
        
        # Update database with VAD results
        audio_file = db.query(AudioFileDB).filter_by(id=audio_file_id).first()
        if audio_file:
            audio_file.speech_segments = json.dumps(vad_result['segments'])
            audio_file.num_speech_segments = vad_result['num_segments']
            audio_file.total_speech_duration = vad_result['speech_duration']
            audio_file.speech_ratio = vad_result['speech_ratio']
            audio_file.duration_seconds = vad_result['total_duration']
            audio_file.vad_processed_at = datetime.utcnow()
            audio_file.status = 'vad_complete'
            
            # If there's speech, add to batch for transcription
            if vad_result['num_segments'] > 0:
                logger.info(f"[VAD] Audio file {audio_file_id} has speech, adding to batch for transcription")
                
                # Get or create batch for this user session
                batch = batch_manager.get_or_create_batch(
                    audio_file.username,
                    audio_file.uploaded_at,
                    db
                )
                
                # Add segment to batch
                batch_manager.add_segment_to_batch(
                    batch,
                    audio_file,
                    vad_result['speech_duration'],
                    db
                )
            else:
                logger.warning(f"[VAD] No speech detected in {audio_file_id}, skipping transcription")
                audio_file.status = 'no_speech'
                db.commit()
            
            logger.info(
                f"VAD complete for {audio_file_id}: "
                f"{vad_result['num_segments']} segments, "
                f"{vad_result['speech_duration']:.1f}s speech / "
                f"{vad_result['total_duration']:.1f}s total "
                f"({vad_result['speech_ratio']*100:.1f}%)"
            )
        
    except Exception as e:
        logger.error(f"[VAD] Error in VAD processing for {audio_file_id}: {e}")
        logger.error(f"[VAD] Failed to process s3://{bucket}/{key}")
        # Update status to failed
        try:
            audio_file = db.query(AudioFileDB).filter_by(id=audio_file_id).first()
            if audio_file:
                audio_file.status = 'vad_failed'
                audio_file.error_message = str(e)
                db.commit()
        except:
            pass
    
    finally:
        # Clean up but keep temp file for now (will be cleaned up later)
        db.close()
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
            logger.debug(f"Cleaned up temp file: {temp_path}")


async def process_s3_event(message: dict, s3_client) -> bool:
    """
    Process an S3 event notification.

    Args:
        message: Parsed SQS message containing S3 event information
        s3_client: Boto3 S3 client

    Returns:
        bool: True if processing succeeded, False otherwise
    """
    bucket = message['bucket']
    key = message['key']
    event_name = message['event_name']
    
    logger.info(f"Processing S3 event: {event_name} for s3://{bucket}/{key}")
    
    # Only process ObjectCreated events
    if not event_name.startswith('ObjectCreated'):
        logger.info(f"Ignoring event type: {event_name}")
        return True  # Not an error, just not relevant
    
    # Extract user information from the S3 key
    # Expected format: native-audio/{username}/segment_*.wav
    # NOTE: Client uploads directly with username, NOT hash
    key_parts = key.split('/')
    if len(key_parts) < 3 or key_parts[0] != 'native-audio':
        logger.warning(f"Unexpected S3 key format: {key}")
        return True  # Not an error, just unexpected format

    # The second part is the actual username (e.g., "yytestbot", "weilyupku@gmail.com")
    user_id = key_parts[1]
    filename = key_parts[2]

    logger.info(f"[S3_EVENT] Processing audio file: {filename} for user: {user_id} from s3://{bucket}/{key}")
    
    # Get file metadata from S3
    try:
        head_response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = head_response.get('ContentLength', 0)
        content_type = head_response.get('ContentType', '')
        
        # Extract capture time from S3 metadata if available
        metadata = head_response.get('Metadata', {})
        logger.info(f"[S3_EVENT] S3 metadata for {key}: {metadata}")
        capture_time = None
        if 'capturedat' in metadata:  # S3 metadata keys are lowercase
            try:
                # Parse Unix timestamp in milliseconds from metadata
                timestamp_ms = float(metadata['capturedat'])
                capture_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                logger.info(f"[S3_EVENT] Parsed capture time from metadata: {capture_time} (from timestamp: {timestamp_ms})")
            except Exception as e:
                logger.warning(f"[S3_EVENT] Failed to parse capture time from metadata '{metadata['capturedat']}': {e}")
        elif 'capture-time' in metadata:
            try:
                # Fallback: Parse ISO format timestamp from metadata  
                capture_time = datetime.fromisoformat(metadata['capture-time'].replace('Z', '+00:00'))
                logger.info(f"Found capture time in ISO metadata: {capture_time}")
            except Exception as e:
                logger.warning(f"Failed to parse ISO capture time from metadata '{metadata['capture-time']}': {e}")
        
        # Determine file format from content type or extension
        file_format = None
        if 'audio' in content_type:
            file_format = content_type.split('/')[-1]
        elif '.' in key:
            file_format = key.split('.')[-1].lower()
        
        logger.info(f"[S3_EVENT] File metadata - Size: {file_size}, Type: {content_type}, Format: {file_format}, Capture time: {capture_time}")
        
    except Exception as e:
        logger.error(f"[S3_EVENT] Error getting S3 object metadata for {key}: {e}")
        file_size = message.get('size', 0)
        file_format = None
        capture_time = None
        logger.warning(f"[S3_EVENT] Using fallback values for {key}: size={file_size}, format={file_format}, capture_time={capture_time}")
    
    # Store in database
    db: Session = SessionLocal()
    try:
        # Check if file already exists in database
        existing_file = db.query(AudioFileDB).filter_by(
            s3_bucket=bucket,
            s3_key=key
        ).first()
        
        if existing_file:
            logger.info(f"[S3_EVENT] File already tracked in database: {existing_file.id}")
            return True  # Already processed, consider it success
        else:
            # Create new audio file record
            s3_upload_time = datetime.fromisoformat(message['event_time'].replace('Z', '+00:00'))
            logger.info(f"[S3_EVENT] Creating DB record - user: {user_id}, s3_upload_time: {s3_upload_time}, capture_time: {capture_time}")
            audio_file = AudioFileDB(
                user_id=None,  # User ID field not used (using username instead)
                username=user_id,  # Using the hashed username from S3 path
                s3_bucket=bucket,
                s3_key=key,
                file_size=file_size,
                format=file_format,
                status="uploaded",
                captured_at=capture_time,  # Use capture time from metadata if available
                uploaded_at=s3_upload_time  # S3 upload time for tracking
            )
            
            db.add(audio_file)
            db.commit()
            db.refresh(audio_file)
            logger.info(f"[S3_EVENT] Database commit successful for {audio_file.id}")
            
            logger.info(f"[S3_EVENT] Successfully created audio file record: {audio_file.id} for s3://{bucket}/{key}, user: {user_id}")

            # Apply VAD processing in background but don't block
            # VAD failures should not prevent database record creation
            asyncio.create_task(apply_vad_processing(audio_file.id, bucket, key))

            # Return success - database record was created successfully
            return True
    
    except Exception as e:
        logger.error(f"[S3_EVENT] Database error processing {key}: {e}")
        logger.error(f"[S3_EVENT] Failed to create database record for s3://{bucket}/{key}, user: {user_id}")
        db.rollback()
        return False  # Failed to create database record
    finally:
        db.close()

    return False  # Should not reach here, but default to failure


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle - start/stop background tasks."""
    global background_task
    
    background_tasks = []
    
    # Check if SQS queue URL is configured
    sqs_queue_url = os.getenv('SQS_QUEUE_URL', '')
    if not sqs_queue_url:
        logger.warning("SQS_QUEUE_URL not configured. SQS polling will not start.")
        logger.warning("Set SQS_QUEUE_URL environment variable to enable S3 event processing.")
    else:
        logger.info(f"SQS Queue URL configured: {sqs_queue_url[:50]}...")
        # Start background task for SQS polling
        background_task = asyncio.create_task(process_sqs_messages())
        background_tasks.append(background_task)
        logger.info("Started SQS polling background task")
        
        # Start batch monitor task
        batch_monitor = asyncio.create_task(batch_monitor_task())
        background_tasks.append(batch_monitor)
        logger.info("Started batch monitor background task")

        # Start S3 reconciliation task to catch missing events
        bucket_name = os.getenv('S3_BUCKET_NAME', 'nirva-audio-1756080156')
        # Create S3 client for reconciliation
        s3_client_reconcile = boto3.client(
            's3',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        reconciliation = asyncio.create_task(
            reconciliation_task(
                bucket_name=bucket_name,
                process_callback=lambda msg: process_s3_event(msg, s3_client_reconcile),
                interval_seconds=60  # Check every 1 minute for testing
            )
        )
        background_tasks.append(reconciliation)
        logger.info("Started S3 reconciliation background task")
    
    yield
    
    # Cleanup
    for task in background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("All background tasks cancelled")


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