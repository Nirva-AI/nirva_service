"""
Database operations for audio files.
"""

from typing import Optional
from sqlalchemy.orm import Session
from loguru import logger

from .pgsql_client import SessionLocal
from .pgsql_object import AudioFileDB


def get_audio_file(audio_file_id: str) -> Optional[AudioFileDB]:
    """
    Get an audio file by ID.
    
    Args:
        audio_file_id: The UUID of the audio file
        
    Returns:
        AudioFileDB object or None if not found
    """
    try:
        session = SessionLocal()
        result = session.query(AudioFileDB).filter(
            AudioFileDB.id == audio_file_id
        ).first()
        session.close()
        return result
    except Exception as e:
        logger.error(f"Error getting audio file {audio_file_id}: {e}")
        return None


def get_audio_file_by_s3_key(s3_key: str) -> Optional[AudioFileDB]:
    """
    Get an audio file by S3 key.
    
    Args:
        s3_key: The S3 object key
        
    Returns:
        AudioFileDB object or None if not found
    """
    try:
        session = SessionLocal()
        result = session.query(AudioFileDB).filter(
            AudioFileDB.s3_key == s3_key
        ).first()
        session.close()
        return result
    except Exception as e:
        logger.error(f"Error getting audio file by s3_key {s3_key}: {e}")
        return None