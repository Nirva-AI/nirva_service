# Deployment & Migration Guide

## Quick Start - Fix Current Issue

SSH into your server and run these commands:

```bash
# 1. SSH into server
ssh -i /path/to/key.pem ec2-user@YOUR_SERVER_IP

# 2. As postgres user, add the missing columns
sudo -u postgres psql nirva << EOF
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS detected_language VARCHAR(10);
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS sentiment_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS topics_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS intents_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS raw_response JSON;
EOF

# 3. Restart the audio processor
source ~/miniconda3/bin/activate nirva
pm2 restart audio-processor-server
```

## Automated Setup for Future Deployments

### 1. Initial Server Setup (Run Once Per New Server)

```bash
# SSH into the new server
ssh -i /path/to/key.pem ec2-user@YOUR_SERVER_IP

# Clone the repository
git clone https://github.com/Nirva-AI/nirva_service.git
cd nirva_service

# Create environment file
cat > .env << EOF
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nirva
DB_USER=nirva
DB_PASSWORD=nirva2025

# Service Configuration
OPENAI_API_KEY=your_openai_key_here
DEEPGRAM_API_KEY=your_deepgram_key_here
REDIS_HOST=localhost
REDIS_PORT=6379

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
EOF

# Copy environment for audio processor
cp .env .env.audio_processor

# Setup conda environment
conda env create -f environment.yml
conda activate nirva

# Install the package
pip install -e .

# Initialize Alembic (for migrations)
alembic init alembic 2>/dev/null || true

# Run initial migrations
alembic upgrade head

# Setup PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup systemd -u ec2-user --hp /home/ec2-user
```

### 2. Regular Deployment Process

From your local machine, run:

```bash
# Option A: Using Makefile (recommended)
make deploy-ec2

# Option B: Manual deployment
./scripts/deploy_to_server.sh YOUR_SERVER_IP

# Option C: Step by step
ssh -i /path/to/key.pem ec2-user@YOUR_SERVER_IP << 'EOF'
cd ~/nirva_service
git pull origin main
source ~/miniconda3/bin/activate nirva
alembic upgrade head
pm2 restart all
EOF
```

### 3. Database Migration Workflow

#### Creating a New Migration (Local Development)

```bash
# 1. Make your model changes in src/nirva_service/db/pgsql_object.py

# 2. Generate migration automatically
alembic revision --autogenerate -m "Description of changes"

# 3. Review the generated migration in alembic/versions/

# 4. Test the migration locally
alembic upgrade head

# 5. Commit and push
git add .
git commit -m "Add migration for new feature"
git push origin main
```

#### Applying Migrations (On Server)

```bash
# Migrations are automatically applied during deployment
# But you can run manually if needed:
ssh -i /path/to/key.pem ec2-user@YOUR_SERVER_IP
cd ~/nirva_service
source ~/miniconda3/bin/activate nirva
alembic upgrade head
```

## Environment Variables

Create `.env` file on each server with:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nirva
DB_USER=nirva
DB_PASSWORD=nirva2025

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# API Keys
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...

# AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/...
S3_BUCKET=nirva-audio-...
```

## Troubleshooting

### Migration Errors

If you get "column already exists" errors:
```bash
# Check current migration status
alembic current

# See migration history
alembic history

# Mark migration as complete without running
alembic stamp head
```

### Database Connection Issues

```bash
# Test database connection
psql -h localhost -U nirva -d nirva -c "SELECT 1"

# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database exists
sudo -u postgres psql -l
```

### Service Issues

```bash
# Check all services
pm2 status

# Check logs
pm2 logs audio-processor-server --lines 100

# Restart specific service
pm2 restart audio-processor-server

# Restart all services
pm2 restart all
```

## PM2 Commands Reference

```bash
pm2 list              # Show all processes
pm2 logs              # Show all logs
pm2 logs [name]       # Show specific service logs
pm2 restart all       # Restart all services
pm2 stop all          # Stop all services
pm2 delete all        # Remove all services
pm2 save              # Save current process list
pm2 resurrect         # Restore saved process list
pm2 startup           # Generate startup script
```

## Database Migration Commands

```bash
alembic init alembic                    # Initialize alembic (once)
alembic revision -m "message"           # Create empty migration
alembic revision --autogenerate -m "msg" # Auto-generate migration
alembic upgrade head                    # Apply all migrations
alembic downgrade -1                    # Rollback one migration
alembic current                         # Show current revision
alembic history                         # Show all migrations
alembic stamp head                      # Mark all as applied
```

## Scaling Considerations

For multiple servers, consider:

1. **Centralized Database**: Use RDS instead of local PostgreSQL
2. **Centralized Redis**: Use ElastiCache instead of local Redis
3. **Environment Management**: Use AWS Systems Manager Parameter Store
4. **Deployment**: Use AWS CodeDeploy or GitHub Actions
5. **Migrations**: Run from a single deployment server or CI/CD pipeline

## Example GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to EC2

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to EC2
        env:
          EC2_HOST: ${{ secrets.EC2_HOST }}
          EC2_USER: ec2-user
          EC2_KEY: ${{ secrets.EC2_KEY }}
        run: |
          echo "$EC2_KEY" > key.pem
          chmod 600 key.pem
          ssh -o StrictHostKeyChecking=no -i key.pem $EC2_USER@$EC2_HOST << 'EOF'
            cd ~/nirva_service
            git pull origin main
            source ~/miniconda3/bin/activate nirva
            alembic upgrade head
            pm2 restart all
          EOF
```