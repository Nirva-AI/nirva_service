#!/bin/bash

# AWS EC2 Sync Script
# Syncs local nirva_service code with AWS EC2 instance
# Usage: ./scripts/sync_aws_with_local.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
EC2_HOST="52.73.87.226"
EC2_USER="ec2-user"
PEM_KEY="/Users/rumiyy/nirva/nirva_service/credentials/aws-my-ec2/my-ec2-key.pem"
REMOTE_DIR="/home/ec2-user/nirva_service"

echo -e "${YELLOW}Starting AWS EC2 sync process...${NC}"

# Check if PEM key exists
if [ ! -f "$PEM_KEY" ]; then
    echo -e "${RED}Error: PEM key not found at $PEM_KEY${NC}"
    exit 1
fi

# Step 1: Ensure local is on main branch and up to date
echo -e "${GREEN}Step 1: Checking local repository...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Warning: Local is on branch '$CURRENT_BRANCH', not 'main'${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get latest commit hash
LOCAL_COMMIT=$(git rev-parse HEAD)
echo "Local commit: $LOCAL_COMMIT"

# Step 2: Connect to AWS and sync
echo -e "${GREEN}Step 2: Connecting to AWS EC2...${NC}"

ssh -i "$PEM_KEY" "$EC2_USER@$EC2_HOST" << 'ENDSSH'
set -e

echo "Connected to AWS EC2"
cd /home/ec2-user/nirva_service

# Stash any local changes
echo "Stashing any local changes..."
git stash -u

# Switch to main branch
echo "Switching to main branch..."
git checkout main

# Pull latest changes
echo "Pulling latest changes..."
git pull origin main

# Get current commit
AWS_COMMIT=$(git rev-parse HEAD)
echo "AWS commit: $AWS_COMMIT"

# Restart services
echo "Restarting services with PM2..."
pm2 restart all

echo "Services restarted successfully"
pm2 list
ENDSSH

echo -e "${GREEN}Step 3: Sync complete!${NC}"
echo -e "${YELLOW}Note: AWS server is now synced with origin/main${NC}"
echo -e "${YELLOW}To sync with your local changes, first push to origin, then run this script${NC}"