#!/bin/bash
# Smart service starter that detects environment and runs migrations

set -e

echo "🚀 Starting Nirva services..."

# Detect environment
if [ -d "/home/ec2-user" ]; then
    echo "📍 Detected EC2 environment"
    CONDA_PATH="/home/ec2-user/miniconda3"
    PROJECT_PATH="/home/ec2-user/nirva_service"
    ECOSYSTEM_FILE="ecosystem.server.config.js"
    USER_HOME="/home/ec2-user"
elif [ -d "/Users/rumiyy" ]; then
    echo "📍 Detected local development environment"
    CONDA_PATH="/Users/rumiyy/anaconda3"
    PROJECT_PATH="/Users/rumiyy/nirva/nirva_service"
    ECOSYSTEM_FILE="ecosystem.config.js"
    USER_HOME="/Users/rumiyy"
else
    echo "⚠️  Unknown environment, using defaults"
    CONDA_PATH="$HOME/miniconda3"
    PROJECT_PATH="$PWD"
    ECOSYSTEM_FILE="ecosystem.config.js"
    USER_HOME="$HOME"
fi

# Change to project directory
cd "$PROJECT_PATH"

# Activate conda environment
source "$CONDA_PATH/bin/activate" nirva

# Check environment files
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file with your configuration"
    exit 1
fi

if [ ! -f ".env.audio_processor" ]; then
    echo "⚠️  Warning: .env.audio_processor not found"
    echo "Creating from .env..."
    cp .env .env.audio_processor
fi

# Run database migrations
echo "🗄️  Running database migrations..."
if [ -f "scripts/run_migration.sh" ]; then
    ./scripts/run_migration.sh
else
    echo "Migration script not found, skipping..."
fi

# Stop existing PM2 processes
echo "🔄 Restarting PM2 services..."
pm2 delete all 2>/dev/null || true

# Kill any processes using our ports
if [ -f "scripts/kill_ports.sh" ]; then
    ./scripts/kill_ports.sh
fi

# Start services with appropriate config
if [ -f "$ECOSYSTEM_FILE" ]; then
    echo "📋 Using config: $ECOSYSTEM_FILE"
    pm2 start "$ECOSYSTEM_FILE"
else
    echo "❌ Ecosystem file not found: $ECOSYSTEM_FILE"
    exit 1
fi

# Save PM2 configuration
pm2 save

# Setup startup script (only on servers)
if [ -d "/home/ec2-user" ]; then
    pm2 startup systemd -u ec2-user --hp /home/ec2-user | grep sudo | bash 2>/dev/null || true
fi

# Show status
echo ""
echo "✅ All services started!"
echo ""
pm2 status

echo ""
echo "📊 Useful commands:"
echo "  pm2 status         - Check service status"
echo "  pm2 logs           - View all logs"
echo "  pm2 logs [name]    - View specific service logs"
echo "  pm2 restart all    - Restart all services"
echo "  pm2 monit          - Monitor services"
echo ""