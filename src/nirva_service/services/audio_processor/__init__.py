"""
Audio Processor Service for handling S3 upload events and transcription.
"""

from .audio_processor_server import app

__all__ = ["app"]