"""
Deepgram transcription service for server-side audio processing.
"""

import os
import json
from typing import Dict, Any, Optional
import aiohttp
from loguru import logger


class DeepgramService:
    """Service for transcribing audio using Deepgram API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Deepgram service.
        
        Args:
            api_key: Deepgram API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            logger.warning("DEEPGRAM_API_KEY not configured")
        
        self.base_url = 'https://api.deepgram.com/v1/listen'
        
    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: str = 'en',
        model: str = 'nova-3'
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Deepgram API.
        
        Args:
            audio_bytes: Audio data in WAV format
            sample_rate: Sample rate of the audio
            language: Language code (auto-detect if not specified)
            model: Deepgram model to use
            
        Returns:
            Dictionary containing transcription and metadata
        """
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not configured")
        
        # Build query parameters
        params = {
            'model': model,
            'detect_language': 'true' if language == 'auto' else 'false',
            'language': language if language != 'auto' else None,
            'punctuate': 'true',
            'utterances': 'true',
            'paragraphs': 'true',
            'smart_format': 'true',
            'diarize': 'false',  # No diarization for single-speaker segments
            'words': 'false',  # Skip word-level data to reduce response size
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        # Create headers
        headers = {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'audio/wav'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    params=params,
                    headers=headers,
                    data=audio_bytes,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Parse the response
                        transcription = self._extract_transcription(result)
                        confidence = self._extract_confidence(result)
                        detected_language = self._extract_language(result)
                        
                        logger.info(
                            f"Transcription successful: {len(transcription)} chars, "
                            f"confidence: {confidence:.2f}, language: {detected_language}"
                        )
                        
                        return {
                            'transcription': transcription,
                            'confidence': confidence,
                            'language': detected_language,
                            'raw_response': result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Deepgram API error {response.status}: {error_text}")
                        raise Exception(f"Deepgram API error {response.status}: {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling Deepgram API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    def _extract_transcription(self, response: Dict[str, Any]) -> str:
        """Extract transcription text from Deepgram response."""
        try:
            results = response.get('results', {})
            channels = results.get('channels', [])
            
            if not channels:
                return ""
            
            channel = channels[0]
            alternatives = channel.get('alternatives', [])
            
            if not alternatives:
                return ""
            
            alternative = alternatives[0]
            
            # Try to get paragraphs first (most readable)
            paragraphs = alternative.get('paragraphs', {})
            if isinstance(paragraphs, dict) and 'transcript' in paragraphs:
                return paragraphs['transcript']
            
            # Fall back to regular transcript
            return alternative.get('transcript', '')
            
        except Exception as e:
            logger.error(f"Error extracting transcription: {e}")
            return ""
    
    def _extract_confidence(self, response: Dict[str, Any]) -> float:
        """Extract confidence score from Deepgram response."""
        try:
            results = response.get('results', {})
            channels = results.get('channels', [])
            
            if not channels:
                return 0.0
            
            channel = channels[0]
            alternatives = channel.get('alternatives', [])
            
            if not alternatives:
                return 0.0
            
            return alternatives[0].get('confidence', 0.0)
            
        except Exception as e:
            logger.error(f"Error extracting confidence: {e}")
            return 0.0
    
    def _extract_language(self, response: Dict[str, Any]) -> str:
        """Extract detected language from Deepgram response."""
        try:
            metadata = response.get('metadata', {})
            return metadata.get('language', 'en')
        except Exception as e:
            logger.error(f"Error extracting language: {e}")
            return 'en'


# Singleton instance
_deepgram_service: Optional[DeepgramService] = None


def get_deepgram_service(api_key: Optional[str] = None) -> DeepgramService:
    """Get or create the singleton Deepgram service instance."""
    global _deepgram_service
    if _deepgram_service is None:
        _deepgram_service = DeepgramService(api_key)
    return _deepgram_service