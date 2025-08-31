#!/bin/bash
# Startup script that runs migrations before starting services
# This should be called by PM2 or systemd on server startup

set -e

echo "🚀 Starting Nirva services..."

# Activate conda environment
source ~/miniconda3/bin/activate nirva

# Change to project directory
cd /home/ec2-user/nirva_service

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head || {
    echo "⚠️ Migration failed, trying to initialize alembic..."
    alembic init alembic 2>/dev/null || true
    alembic upgrade head || echo "⚠️ Migrations skipped"
}

# Start all services with PM2
echo "🔄 Starting services with PM2..."
pm2 start ecosystem.config.js
pm2 save
pm2 startup systemd -u ec2-user --hp /home/ec2-user || true

echo "✅ Services started successfully!"
pm2 list