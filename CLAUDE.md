# CLAUDE.md - nirva_service

Server-specific documentation for nirva_service backend.

## API Endpoints

### Authentication
- **POST /login/v1/** - OAuth2 login (form data: username, password)
- **POST /logout/** - End session
- **GET /health/** - Health check

### Mental State
- **GET /mental_state/timeline** - Get mental state timeline (30-min intervals)
  - Returns energy_score and stress_score (0-100 scale)
  - Last 4 points may be 0 from AWS (workaround: use last non-zero)
- **GET /mental_state/current** - Get current mental state
- **POST /mental_state/update** - Update mental state with events

### Events & Transcriptions
- **GET /events** - List user events
- **POST /events** - Create new event
- **GET /transcriptions** - List transcriptions
- **POST /transcriptions/analyze** - Trigger transcript analysis
- **GET /transcriptions/{id}/status** - Check analysis status

### Journal (Legacy)
- **GET /journal/entries** - List journal entries
- **POST /journal/entries** - Create journal entry
- **PUT /journal/entries/{id}** - Update journal entry

## Database Schema

### Key Tables
```sql
-- Users table
users (
  id, username, email, password_hash, created_at, updated_at
)

-- Events table (replaced journal files)
events (
  event_id, user_id, username, event_type, description,
  energy_impact, stress_impact, mood_impact,
  start_timestamp, end_timestamp, created_at
)

-- Transcription results
transcription_results (
  id, username, transcription_text, start_time, end_time,
  analysis_status, analyzed_at, created_at
)

-- Mental state scores
mental_state_scores (
  id, user_id, event_id, energy_score, stress_score, mood_score,
  timestamp, data_source, created_at
)
```

### Status Values
- Transcription status: pending, processing, completed, failed
- Event types: work, exercise, social, meal, break, sleep, other

## Mental State Calculation

### Baseline Curves (0-100 scale)
```python
energy_curve = {
    0: 30,   # Midnight
    3: 20,   # Deep sleep
    6: 45,   # Wake up
    9: 70,   # Morning peak
    12: 60,  # Lunch dip
    15: 55,  # Afternoon
    18: 50,  # Evening
    21: 35,  # Wind down
    23: 30   # Pre-sleep
}

stress_curve = {
    0: 20,   # Midnight
    3: 10,   # Deep sleep
    6: 25,   # Wake up
    9: 45,   # Work start
    12: 60,  # Midday pressure
    15: 70,  # Afternoon peak
    18: 45,  # Evening relief
    21: 30,  # Relaxation
    23: 20   # Pre-sleep
}
```

### Event Impact Calculation
1. Get baseline value from curve
2. Apply event impacts (additive)
3. Clamp to 0-100 range
4. Generate 30-minute interval timeline

## AWS Deployment

### Connection
```bash
ssh -i credentials/aws-my-ec2/my-ec2-key.pem ec2-user@52.73.87.226
cd /home/ec2-user/nirva_service
```

### Deployment Commands
```bash
# Local: sync to AWS
./scripts/sync_aws_with_local.sh

# On AWS: manual operations
pm2 list              # View services
pm2 restart all       # Restart all
pm2 logs appservice   # View logs
git status            # Check branch (should be main)
```

### Database Connection
- Database: my_fastapi_db
- User: fastapi_user
- Host: AWS RDS instance
- Pool size: 20 connections
- Max overflow: 40 connections

## Service Configuration

### Environment Variables (.env)
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET_KEY=...
```

### Service Ports
- AppService: 8000
- Chat Server: 8100  
- Analyzer Server: 8200
- Audio Processor Server: 8300

### PM2 Process Names
- appservice
- chat
- analyzer
- audio-processor

## Common Operations

### Reset Transcriptions
```bash
python scripts/reset_transcriptions_for_reprocessing.py \
  --username yytestbot \
  --dates 2025-09-08,2025-09-09 \
  --execute
```

### Clear Database (Dev Only)
```bash
make clear-db
```

### Run Type Checking
```bash
make type-check      # Key scripts only
make type-check-all  # All source code
```

### Format Code
```bash
make format  # black + isort
make lint    # flake8
```

## Recent Changes (Sept 2025)

1. **Mental State Scale Update**: Changed from 1-10 to 0-100 scale
   - Updated all Field validators in Pydantic models
   - Adjusted baseline curves to 0-100 range
   - Fixed stress_curve values (were 10-55, now proper 0-100)

2. **Event System**: Replaced journal file storage with database events
   - Events extracted from transcripts by analyzer
   - Each event has impact scores for energy/stress/mood
   - Mental state calculated from baseline + event impacts

3. **AWS Sync**: Automated deployment via sync script
   - Switched from yh-aws-ec2-linux branch to main
   - Added script for resetting transcriptions
   - PM2 manages all services

4. **Dashboard Fix**: Fixed 0 values in dashboard
   - AWS returns last 4 timeline points as 0
   - Client now finds last non-zero value
   - Charts and dashboard use timeline data directly