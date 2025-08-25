# AWS Migration and Audio Pipeline Implementation

## Overview

This document describes the complete process of migrating from a shared AWS account to a dedicated AWS account and implementing an S3-based audio processing pipeline with SQS event notifications.

## Background

The Nirva application originally used two separate backend systems:
1. **AWS Amplify** - For authentication (Cognito) and storage (S3)
2. **nirva_service** - Custom Python backend for business logic

The goal was to consolidate to a single backend (nirva_service) and migrate to a dedicated AWS account with proper audio file processing.

## Architecture

### Before Migration
```
Flutter App → AWS Amplify (Cognito + S3)
           → nirva_service (Business Logic)
```

### After Migration
```
Flutter App → nirva_service → AWS (S3 + SQS)
                            → Audio Processor
```

## Phase 1: Authentication Consolidation

### Problem
- Dual authentication systems (Amplify Cognito + Custom JWT)
- Client needed to manage two different auth flows
- S3 uploads were unauthenticated through Amplify

### Solution Implemented

1. **JWT Authentication Fix**
   - Fixed critical timezone bug in JWT token generation
   - Changed from `datetime.now()` to `datetime.utcnow()` in `/src/nirva_service/db/jwt.py`
   - Fixed Redis token expiration from 60 seconds to 3600 seconds (1 hour)

2. **S3 Upload Token Endpoint**
   - Created `/action/auth/s3-upload-token/v1/` endpoint
   - Returns temporary AWS STS credentials (36-hour validity)
   - Credentials scoped to user-specific S3 prefix
   - Client manages 12-hour refresh cooldown

3. **AWS STS Service**
   - Implemented in `/src/nirva_service/services/storage/aws_sts_service.py`
   - Generates temporary credentials using AWS STS GetSessionToken
   - Returns bucket name, prefix, and temporary credentials to client

## Phase 2: Audio Processing Pipeline

### Architecture
```
S3 Upload → S3 Event → SQS Queue → Audio Processor → Database
                                 ↓
                        Transcription Service (Future)
```

### Components Implemented

1. **Audio Processor Server** (Port 8300)
   - New microservice for processing audio files
   - Polls SQS queue for S3 event notifications
   - Creates database records for uploaded files
   - Prepared for transcription service integration

2. **Database Schema**
   - Added `AudioFileDB` model in `/src/nirva_service/db/pgsql_object.py`
   - Tracks: user_id, s3_bucket, s3_key, status, timestamps
   - Status workflow: uploaded → processing → transcribed → completed

3. **SQS Service**
   - Implemented in `/src/nirva_service/services/storage/sqs_service.py`
   - Long polling (20 seconds) for efficiency
   - Batch message processing
   - Automatic message deletion after processing

## Phase 3: AWS Account Migration

### Process

1. **Created New AWS Account** (ID: 275863577408)
   - Set up with IAM admin user (not root)
   - Enabled MFA for security
   - Configured billing alerts

2. **Resources Created**
   - **S3 Bucket**: `nirva-audio-1756080156`
     - Versioning enabled
     - Lifecycle policy (90-day deletion)
   - **SQS Queue**: `nirva-audio-queue`
     - 4-day message retention
     - 5-minute visibility timeout
   - **IAM User**: `nirva-app`
     - Minimal permissions (S3, SQS, STS)
     - Separate credentials for audio processor

3. **S3 Event Notifications**
   - Configured for multiple prefixes:
     - `audio/` - General audio files
     - `native-audio/` - iOS native uploads
     - `users/` - User-specific uploads
   - All events sent to SQS queue

### Migration Steps Performed

1. **Environment Configuration**
   ```bash
   # Backed up old credentials
   cp .env .env.backup_old_aws
   
   # Applied new AWS credentials
   cp .env.my_aws .env
   cp .env.my_aws .env.audio_processor
   ```

2. **Service Updates**
   - Updated PM2 scripts to include audio processor
   - Modified `kill_ports.sh` to include port 8300
   - Added `make run-audio-processor` to Makefile

3. **Client Updates**
   - S3 credentials cached for 12 hours
   - Force refresh by uninstalling/reinstalling app
   - Server now returns new bucket name dynamically

## Current State

### Working Features
- ✅ JWT authentication with nirva_service
- ✅ S3 upload with temporary credentials
- ✅ S3 event notifications via SQS
- ✅ Audio processor receiving events
- ✅ Database tracking of uploaded files
- ✅ Complete migration to dedicated AWS account

### AWS Free Tier Usage
- **S3**: 5GB storage, 20k GET/2k PUT requests/month
- **SQS**: 1 million messages/month (forever free)
- **EC2**: 750 hours t2.micro/month (12 months)
- **Estimated cost after free tier**: $15-20/month

## File Structure

### New Files Created
```
/src/nirva_service/
├── services/
│   ├── storage/
│   │   ├── aws_sts_service.py      # STS credential generation
│   │   └── sqs_service.py           # SQS message polling
│   └── audio_processor/
│       └── audio_processor_server.py # Audio processing service
├── config/
│   └── configuration.py              # Added AudioProcessorServerConfig
└── db/
    └── pgsql_object.py               # Added AudioFileDB model

/scripts/
├── run_audio_processor_server.py     # Audio processor launcher
├── setup_my_aws.py                   # AWS setup utility
└── fix_s3_notifications.py           # S3 notification utility
```

### Configuration Files
```
.env                      # Main environment variables
.env.audio_processor      # Audio processor specific credentials
ecosystem.config.js       # PM2 configuration
```

## Running the System

### Start All Services
```bash
make run-all
# or
./scripts/run_pm2script.sh
```

### Individual Services
```bash
make run-appservice         # Port 8000
make run-chat              # Port 8100
make run-analyzer          # Port 8200
make run-audio-processor   # Port 8300
```

### Monitor Services
```bash
pm2 status                              # Check all services
pm2 logs audio-processor-server         # View audio processor logs
pm2 logs --lines 50                     # View all logs
```

## Next Steps

### Immediate
1. Implement transcription service integration (AWS Transcribe or Deepgram)
2. Add audio file processing logic (format validation, duration limits)
3. Implement webhook notifications for transcription completion

### Future Enhancements
1. Add Lambda functions for serverless audio processing
2. Implement CloudFront CDN for audio file delivery
3. Add audio file compression and optimization
4. Implement real-time transcription streaming
5. Add support for multiple audio formats

## Troubleshooting

### Common Issues

1. **S3 Events Not Received**
   - Check S3 bucket notification configuration
   - Verify SQS queue permissions
   - Ensure files match configured prefix filters

2. **Authentication Errors**
   - Verify JWT token has correct UTC time
   - Check Redis connection and token storage
   - Ensure client is sending Bearer token correctly

3. **AWS Permission Errors**
   - Check IAM user policies
   - Verify SQS queue access policy
   - Ensure S3 bucket policy allows uploads

### Debug Commands
```bash
# Check SQS queue attributes
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/275863577408/nirva-audio-queue \
  --attribute-names All

# List S3 bucket contents
aws s3 ls s3://nirva-audio-1756080156/ --recursive

# Test S3 upload
echo "test" | aws s3 cp - s3://nirva-audio-1756080156/test.txt

# View audio processor logs
pm2 logs audio-processor-server --lines 100
```

## Security Considerations

1. **Credentials Management**
   - Never commit AWS credentials to git
   - Use separate IAM users for different services
   - Rotate credentials regularly

2. **S3 Security**
   - User-scoped prefixes prevent cross-user access
   - Temporary credentials expire after 36 hours
   - Bucket versioning enabled for data recovery

3. **SQS Security**
   - Queue policy restricts access to specific S3 bucket
   - Messages deleted after successful processing
   - Dead letter queue for failed messages (to be implemented)

## Cost Optimization

1. **S3 Lifecycle Policies**
   - Auto-delete files after 90 days
   - Move to Glacier for long-term storage
   - Use S3 Intelligent-Tiering

2. **SQS Optimization**
   - Long polling reduces API calls
   - Batch processing reduces costs
   - Message deduplication (to be implemented)

3. **Monitoring**
   - Set billing alerts at $5, $10, $20
   - Use AWS Cost Explorer
   - Regular review of resource usage

## References

- [AWS STS Documentation](https://docs.aws.amazon.com/STS/latest/APIReference/)
- [S3 Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html)
- [SQS Long Polling](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-short-and-long-polling.html)
- [AWS Free Tier](https://aws.amazon.com/free/)