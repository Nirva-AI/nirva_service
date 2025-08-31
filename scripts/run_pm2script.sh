#!/bin/bash

# Check if .env files exist
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    exit 1
fi

if [ ! -f ".env.audio_processor" ]; then
    echo "Warning: .env.audio_processor file not found!"
    echo "Audio processor service may not work correctly without its credentials."
fi

# Load main environment variables for this script
set -a  # automatically export all variables
source .env
set +a  # stop automatically exporting

echo "Environment check completed!"

# Run database migrations before starting services
echo "Running database migrations..."
if [ -f "scripts/run_migration.sh" ]; then
    ./scripts/run_migration.sh
elif command -v alembic &> /dev/null; then
    alembic upgrade head 2>/dev/null || echo "Migrations skipped (alembic not configured or no pending migrations)"
else
    echo "Migration system not configured, skipping..."
fi

# Delete all pm2 processes
pm2 delete all

# Kill any processes using our ports
./scripts/kill_ports.sh

# Start all services using ecosystem file
# PM2 will handle loading the correct env files for each service
pm2 start ecosystem.config.js

echo "All servers started using PM2 ecosystem configuration!"
echo "Use 'pm2 status' to check service status"
echo "Use 'pm2 logs' to view logs"
echo "Use 'pm2 logs audio-processor-server' to view specific service logs"
