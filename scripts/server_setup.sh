#!/bin/bash
# One-time server setup script for new EC2 instances
# Run this on the server after initial SSH

set -e

echo "🚀 Starting Nirva Service Server Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if running on EC2
if [ ! -f /etc/system-release ] || ! grep -q "Amazon Linux" /etc/system-release; then
    print_warning "This script is designed for Amazon Linux EC2. Proceed with caution."
fi

# 1. Update system packages
print_status "Updating system packages..."
sudo yum update -y

# 2. Install PostgreSQL if not installed
if ! command -v psql &> /dev/null; then
    print_status "Installing PostgreSQL..."
    sudo yum install -y postgresql15 postgresql15-server
    sudo postgresql-setup --initdb
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
else
    print_status "PostgreSQL already installed"
fi

# 3. Setup PostgreSQL database
print_status "Setting up PostgreSQL database..."
sudo -u postgres psql << EOF 2>/dev/null || true
CREATE USER nirva WITH PASSWORD 'nirva2025';
CREATE DATABASE nirva OWNER nirva;
GRANT ALL PRIVILEGES ON DATABASE nirva TO nirva;
EOF

# 4. Install Redis if not installed
if ! command -v redis-cli &> /dev/null; then
    print_status "Installing Redis..."
    sudo yum install -y redis6
    sudo systemctl enable redis6
    sudo systemctl start redis6
else
    print_status "Redis already installed"
fi

# 5. Install Miniconda if not installed
if [ ! -d ~/miniconda3 ]; then
    print_status "Installing Miniconda..."
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
    bash ~/miniconda.sh -b -p ~/miniconda3
    rm ~/miniconda.sh
    echo 'export PATH="~/miniconda3/bin:$PATH"' >> ~/.bashrc
    source ~/.bashrc
else
    print_status "Miniconda already installed"
fi

# 6. Clone repository if not exists
if [ ! -d ~/nirva_service ]; then
    print_status "Cloning repository..."
    git clone https://github.com/Nirva-AI/nirva_service.git ~/nirva_service
else
    print_status "Repository already cloned"
    cd ~/nirva_service
    git pull origin main
fi

cd ~/nirva_service

# 7. Create environment file if not exists
if [ ! -f .env ]; then
    print_status "Creating environment file..."
    cat > .env << 'EOF'
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nirva
DB_USER=nirva
DB_PASSWORD=nirva2025

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# API Keys (REPLACE THESE!)
OPENAI_API_KEY=sk-YOUR_KEY_HERE
DEEPGRAM_API_KEY=YOUR_KEY_HERE

# AWS Configuration (REPLACE THESE!)
AWS_ACCESS_KEY_ID=YOUR_KEY_HERE
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_HERE
AWS_REGION=us-east-1
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT/YOUR_QUEUE
S3_BUCKET=YOUR_BUCKET_NAME
EOF
    
    cp .env .env.audio_processor
    print_warning "Please edit .env file with your actual API keys!"
else
    print_status "Environment file already exists"
fi

# 8. Setup conda environment
print_status "Setting up conda environment..."
source ~/miniconda3/bin/activate
conda env create -f environment.yml 2>/dev/null || conda env update -f environment.yml
conda activate nirva

# 9. Install package
print_status "Installing nirva_service package..."
pip install -e .

# 10. Run database migrations
print_status "Running database migrations..."
# First, ensure alembic is initialized
if [ ! -d alembic ]; then
    alembic init alembic 2>/dev/null || true
fi

# Create migration table if needed
python << 'EOF'
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://nirva:nirva2025@localhost/nirva')
with engine.connect() as conn:
    # Create alembic version table if it doesn't exist
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
    """))
    conn.commit()
    
    # Add the missing columns directly (for immediate fix)
    try:
        conn.execute(text("""
            ALTER TABLE transcription_results 
            ADD COLUMN IF NOT EXISTS detected_language VARCHAR(10),
            ADD COLUMN IF NOT EXISTS sentiment_data JSON,
            ADD COLUMN IF NOT EXISTS topics_data JSON,
            ADD COLUMN IF NOT EXISTS intents_data JSON,
            ADD COLUMN IF NOT EXISTS raw_response JSON
        """))
        conn.commit()
        print("✓ Database columns added successfully")
    except Exception as e:
        print(f"⚠ Column creation skipped: {e}")
EOF

# 11. Install PM2 if not installed
if ! command -v pm2 &> /dev/null; then
    print_status "Installing PM2..."
    npm install -g pm2
else
    print_status "PM2 already installed"
fi

# 12. Start services with PM2
print_status "Starting services with PM2..."
pm2 delete all 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save
pm2 startup systemd -u ec2-user --hp /home/ec2-user | grep sudo | bash

# 13. Show status
print_status "Setup complete! Service status:"
pm2 list

echo ""
echo "========================================="
echo "         Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your actual API keys"
echo "2. Restart services: pm2 restart all"
echo "3. Check logs: pm2 logs"
echo ""
echo "To deploy updates in the future, run:"
echo "  cd ~/nirva_service"
echo "  git pull origin main"
echo "  source ~/miniconda3/bin/activate nirva"
echo "  pm2 restart all"
echo ""