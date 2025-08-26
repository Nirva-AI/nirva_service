# Journal: Audio Processing Server Implementation

**Date:** August 25-26, 2024  
**Author:** Development Team  
**Status:** ✅ Complete and Working

## Overview

Successfully implemented a complete audio processing pipeline with S3 event-driven architecture, Voice Activity Detection (VAD), intelligent batching, and Deepgram transcription. The system processes audio files uploaded to S3, extracts speech segments, batches them for context, and transcribes only the speech portions for cost efficiency.

## Architecture Components

### 1. S3 Event Processing
- **S3 Bucket:** `nirva-audio-1756080156`
- **Upload Path:** `native-audio/{encoded_user_id}/segment_*.wav`
- **Event Notifications:** S3 → SQS Queue
- **SQS Queue:** `nirva-audio-queue` (Account: 275863577408)

### 2. Audio Processor Server
- **Port:** 8300
- **Background Tasks:**
  - SQS Polling (continuous)
  - Batch Monitor (every 10 seconds)
- **Environment:** `.env.audio_processor`

### 3. Voice Activity Detection (VAD)
- **Model:** Silero VAD v4 with ONNX runtime
- **Purpose:** Detect speech segments in audio files
- **Configuration:**
  - Min speech duration: 250ms
  - Min silence duration: 100ms
  - Threshold: 0.5
  - Speech padding: 30ms

### 4. Batch Processing
- **MAX_GAP:** 30 seconds (conversation boundary)
- **TIMEOUT:** 2 minutes (batch processing trigger)
- **Strategy:** Accumulate related audio segments for better transcription context

### 5. Transcription Service
- **Provider:** Deepgram
- **Model:** nova-3
- **Optimization:** Only transcribe extracted speech segments (not silence)
- **Features:** Smart formatting, punctuation, utterances, paragraphs

## Implementation Timeline

### Phase 1: AWS Migration
- Migrated from shared AWS account (256105712922) to dedicated account (275863577408)
- Created new S3 bucket, SQS queue, and IAM users
- Fixed S3 event notifications to watch correct prefix (`native-audio/`)

### Phase 2: Database Models
```python
# New tables created:
- AudioBatchDB: Track segment batches
- TranscriptionResultDB: Store transcription results
- Updated AudioFileDB: Added batch_id field
```

### Phase 3: Core Services

#### VAD Service (`vad_service.py`)
- Implemented Silero VAD v4 integration
- Added `extract_and_concat_speech()` for multi-file processing
- Returns speech segments with timestamps

#### Deepgram Service (`deepgram_service.py`)
- Async API client for Deepgram
- Handles WAV audio transcription
- Returns text with confidence scores

#### Batch Manager (`batch_manager.py`)
- Manages segment accumulation
- Handles time-based batching logic
- Tracks batch lifecycle (accumulating → processing → completed)

#### Audio Processor Server (`audio_processor_server.py`)
- Main orchestrator for the pipeline
- Integrates VAD, batching, and transcription
- Background tasks for SQS polling and batch monitoring

### Phase 4: Bug Fixes

1. **Database Column Missing**
   - Error: `column audio_files.batch_id does not exist`
   - Fix: Added column with ALTER TABLE

2. **Timezone Issues**
   - Error: `can't subtract offset-naive and offset-aware datetimes`
   - Fix: Updated to use `datetime.now(timezone.utc)`

3. **Import Missing**
   - Error: `name 'timedelta' is not defined`
   - Fix: Added timedelta import

## Configuration

### Environment Variables (`.env.audio_processor`)
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_BUCKET=nirva-audio-1756080156
AWS_ACCESS_KEY_ID=AKIAUAOWAENABHQEBGVD
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/275863577408/nirva-audio-queue

# API Keys
DEEPGRAM_API_KEY=2c65edd89aec3c662f07ca18924054f2408ddf08

# Batch Processing
BATCH_MAX_GAP_SECONDS=30
BATCH_TIMEOUT_SECONDS=120
```

## Processing Flow

1. **Audio Upload** → S3 bucket (`native-audio/` prefix)
2. **S3 Event** → SQS Queue notification
3. **SQS Polling** → Audio processor receives message
4. **Download & VAD** → Process audio, detect speech segments
5. **Batching** → Add to batch if speech detected
6. **Timeout Monitor** → After 2 minutes, trigger processing
7. **Speech Extraction** → Extract only speech portions
8. **Transcription** → Send to Deepgram (only speech audio)
9. **Storage** → Save transcription with time range

## Performance Results

### First Successful Transcription
- **Files:** 2 audio segments
- **Total Audio Duration:** ~60 seconds
- **Speech Duration:** 7.7 seconds
- **Confidence:** 94.77%
- **Text:** "Automatic audio capture started successfully. Six. Cloud audio processor already initialized. Cloud audio"
- **Cost Savings:** ~87% (only transcribed 7.7s instead of 60s)

## Key Features

### 1. Cost Optimization
- Only transcribe speech segments, not silence
- Batch multiple segments in single API call
- Example: 7.7s speech from 60s audio = 87% cost reduction

### 2. Context Preservation
- Batch related segments together
- 2-minute timeout ensures timely processing
- 30-second gap detection for conversation boundaries

### 3. Fault Tolerance
- Retry mechanism for failed processing
- Database tracking of processing status
- SQS visibility timeout for message retry

### 4. Real-time Processing
- Continuous SQS polling
- Background batch monitoring
- Automatic processing after timeout

## Commands Reference

### Start Services
```bash
# Always activate environment first
source ~/anaconda3/etc/profile.d/conda.sh && conda activate nirva

# Start all services with PM2
./scripts/run_pm2script.sh

# Check status
pm2 status

# View logs
pm2 logs audio-processor-server
```

### Database Operations
```bash
# Create tables
python -c "
from nirva_service.db.pgsql_client import engine
from nirva_service.db.pgsql_object import Base
Base.metadata.create_all(bind=engine)
"

# Check processing status
python -c "
from nirva_service.db.pgsql_client import SessionLocal
from nirva_service.db.pgsql_object import AudioBatchDB, TranscriptionResultDB
db = SessionLocal()
# Query batches and transcriptions
"
```

## Lessons Learned

1. **Timezone Consistency:** Always use timezone-aware datetimes in distributed systems
2. **Batch Processing:** Balancing latency vs context - 2 minutes provides good compromise
3. **Cost Efficiency:** VAD + speech extraction dramatically reduces transcription costs
4. **Error Handling:** Proper status tracking prevents stuck batches
5. **Environment Management:** Separate `.env.audio_processor` for service-specific config

## Future Enhancements

1. **Adaptive Batching:** Adjust timeout based on conversation patterns
2. **Multi-language Support:** Auto-detect and handle different languages
3. **Speaker Diarization:** Identify different speakers in conversations
4. **Real-time Streaming:** WebSocket support for live transcription updates
5. **Analytics Dashboard:** Visualize processing metrics and costs

## Conclusion

The audio processing server successfully demonstrates a production-ready pipeline for handling audio transcription at scale. The combination of event-driven architecture, intelligent batching, and speech extraction provides a cost-effective and efficient solution for audio-to-text processing.

**Key Achievement:** Reduced transcription costs by ~87% while maintaining high accuracy (94.77% confidence) by only processing speech segments.