#!/bin/bash

# Setup script for PM2 on server
# This script helps configure PM2 for server deployment

echo "Setting up PM2 configuration for server..."

# Check if we're on a server (not local development)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Detected Linux server environment"
    
    # Find Python interpreter
    PYTHON_PATH=$(which python3)
    if [ -z "$PYTHON_PATH" ]; then
        PYTHON_PATH=$(which python)
    fi
    
    if [ -z "$PYTHON_PATH" ]; then
        echo "ERROR: Python not found. Please install Python 3.x"
        exit 1
    fi
    
    echo "Using Python interpreter: $PYTHON_PATH"
    
    # Update ecosystem config with correct Python path
    sed -i "s|interpreter: 'python3'|interpreter: '$PYTHON_PATH'|g" ecosystem-server.config.js
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    # Install PM2 if not already installed
    if ! command -v pm2 &> /dev/null; then
        echo "Installing PM2..."
        npm install -g pm2
    fi
    
    # Stop any existing PM2 processes
    pm2 delete all 2>/dev/null || true
    
    # Start services with server config
    echo "Starting services with server configuration..."
    pm2 start ecosystem-server.config.js
    
    # Save PM2 configuration
    pm2 save
    
    # Setup PM2 to start on boot
    pm2 startup
    
    echo "PM2 setup complete!"
    echo "Use 'pm2 status' to check service status"
    echo "Use 'pm2 logs' to view logs"
    
else
    echo "This script is intended for server environments (Linux)"
    echo "For local development, use: pm2 start ecosystem.config.js"
fi
