#!/bin/bash

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    set -a  # automatically export all variables
    source .env
    set +a  # stop automatically exporting
    echo "Environment variables loaded successfully!"
    echo "OPENAI_API_KEY length: ${#OPENAI_API_KEY}"
else
    echo "Warning: .env file not found!"
    exit 1
fi

# 删除所有 pm2 进程
pm2 delete all

./scripts/kill_ports.sh

# Export environment variables for PM2 processes
export OPENAI_API_KEY

# 启动指定的 Python 脚本 (make sure to activate conda env first)
pm2 start scripts/run_chat_server.py --name chat-server
pm2 start scripts/run_analyzer_server.py --name analyzer-server
pm2 start scripts/run_appservice_server.py --name appservice-server

echo "All servers started with environment variables loaded!"
echo "Note: Make sure to activate the correct conda environment before running this script"
