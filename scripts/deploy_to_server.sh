#!/bin/bash
# Automated deployment script for nirva_service

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Configuration
SERVER_IP="${1:-52.73.87.226}"  # Pass server IP as first argument
KEY_PATH="${2:-/Users/rumiyy/nirva/nirva_service/credentials/aws-my-ec2/my-ec2-key.pem}"
SERVER_USER="ec2-user"
PROJECT_PATH="/home/ec2-user/nirva_service"

echo "📦 Deploying to: $SERVER_USER@$SERVER_IP"

# 1. Pull latest code on server
echo "📥 Pulling latest code..."
ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
cd /home/ec2-user/nirva_service
git stash
git pull origin main
ENDSSH

# 2. Run database migrations
echo "🗄️ Running database migrations..."
ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
cd /home/ec2-user/nirva_service
source ~/miniconda3/bin/activate nirva

# Set database credentials from .env file if it exists
if [ -f .env.audio_processor ]; then
    export $(grep -v '^#' .env.audio_processor | xargs)
fi

# Run alembic migrations
alembic upgrade head || echo "⚠️ Migration failed or already applied"
ENDSSH

# 3. Restart services
echo "🔄 Restarting services..."
ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
source ~/miniconda3/bin/activate nirva
pm2 restart all
pm2 save
ENDSSH

echo "✅ Deployment complete!"
echo "📊 Service status:"
ssh -i "$KEY_PATH" "$SERVER_USER@$SERVER_IP" "pm2 list"