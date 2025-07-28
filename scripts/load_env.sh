#!/bin/bash

# Load environment variables from .env file
# Usage: source scripts/load_env.sh

if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    set -a  # automatically export all variables
    source .env
    set +a  # stop automatically exporting
    echo "Environment variables loaded successfully!"
else
    echo "Warning: .env file not found!"
    echo "Please create a .env file with your OpenAI API key:"
    echo "OPENAI_API_KEY=your-actual-openai-api-key-here"
fi 