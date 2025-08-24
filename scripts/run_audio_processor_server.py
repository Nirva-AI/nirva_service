#!/usr/bin/env python
"""
Script to run the Audio Processor Server.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import uvicorn
from nirva_service.config.configuration import AudioProcessorServerConfig

if __name__ == "__main__":
    # Load audio processor specific environment variables
    audio_env_path = Path(__file__).parent.parent / '.env.audio_processor'
    if audio_env_path.exists():
        print(f"Loading audio processor environment from: {audio_env_path}")
        load_dotenv(audio_env_path, override=True)
    else:
        print("Warning: .env.audio_processor not found, using default .env")
        load_dotenv(override=True)
    
    config = AudioProcessorServerConfig()
    
    print(f"Starting Audio Processor Server on port {config.port}...")
    print(f"SQS Queue URL: {os.getenv('SQS_QUEUE_URL', 'Not configured')}")
    print(f"Using AWS Access Key: {os.getenv('AWS_ACCESS_KEY_ID', 'Not configured')[:20]}...")
    
    uvicorn.run(
        "nirva_service.services.audio_processor:app",
        host="0.0.0.0",
        port=config.port,
        reload=True,
        log_level="info"
    )