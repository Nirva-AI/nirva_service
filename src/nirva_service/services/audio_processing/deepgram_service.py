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
        language: str = 'auto',  # Changed to auto-detect by default
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
        
        # Build query parameters - MATCH CLIENT CONFIGURATION EXACTLY
        params = {
            'model': model,  # nova-3
            'detect_language': 'true',  # ALWAYS enable language detection for multilingual support
            'diarize': 'true',  # Enable speaker diarization (matches client)
            'punctuate': 'true',  # Enable punctuation
            'utterances': 'true',  # Enable utterances
            'paragraphs': 'true',  # Group transcript into readable paragraphs
            # 'smart_format': 'true',  # REMOVED - causes spacing issues with Chinese characters
            'words': 'true',  # Enable word-level data for better timing and punctuation
            'sentiment': 'true',  # Enable sentiment analysis (matches client)
            'topics': 'true',  # Enable topic detection (matches client)
            'intents': 'true',  # Enable intent recognition (matches client)
        }
        
        # Only add language parameter if not auto-detecting
        if language != 'auto':
            params['language'] = language
        
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
                        sentiment_data = self._extract_sentiment(result)
                        topics_data = self._extract_topics(result)
                        intents_data = self._extract_intents(result)
                        
                        logger.info(
                            f"Transcription successful: {len(transcription)} chars, "
                            f"confidence: {confidence:.2f}, language: {detected_language}"
                        )
                        
                        if sentiment_data:
                            logger.info(f"Sentiment analysis available: {len(sentiment_data)} segments")
                        if topics_data:
                            logger.info(f"Topics detected: {len(topics_data)} topics")
                        if intents_data:
                            logger.info(f"Intents recognized: {len(intents_data)} intents")
                        
                        return {
                            'transcription': transcription,
                            'confidence': confidence,
                            'language': detected_language,
                            'sentiment_data': sentiment_data,
                            'topics_data': topics_data,
                            'intents_data': intents_data,
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
        import re
        
        try:
            results = response.get('results', {})
            
            # Use utterances for better formatting
            utterances = results.get('utterances', [])
            if utterances:
                # Check how many unique speakers there are
                unique_speakers = set()
                for utt in utterances:
                    speaker = utt.get('speaker')
                    if speaker is not None:
                        unique_speakers.add(speaker)
                
                # Determine if we need speaker prefixes
                has_multiple_speakers = len(unique_speakers) > 1
                
                # Get language for proper spacing
                detected_lang = self._extract_language(response)
                is_cjk = detected_lang in ['zh', 'zh-CN', 'zh-TW', 'zh-hans', 'zh-hant', 'ja', 'ko']
                
                # Build transcript from utterances
                transcripts = []
                last_speaker = None
                
                for utt in utterances:
                    text = utt.get('transcript', '').strip()
                    if not text:
                        continue
                        
                    speaker = utt.get('speaker')
                    
                    # Add speaker prefix only if multiple speakers
                    if has_multiple_speakers and speaker is not None:
                        # Add speaker label if speaker changed
                        if speaker != last_speaker:
                            transcripts.append(f"\nSpeaker {speaker}: {text}")
                            last_speaker = speaker
                        else:
                            transcripts.append(text)
                    else:
                        # Single speaker - no prefix needed
                        transcripts.append(text)
                
                # Join with appropriate spacing
                if has_multiple_speakers:
                    # For multi-speaker, join with space (speaker labels handle separation)
                    full_transcript = ' '.join(transcripts).strip()
                elif is_cjk:
                    # For single-speaker CJK, join without extra spaces
                    full_transcript = ''.join(transcripts)
                else:
                    # For single-speaker non-CJK, join with space
                    full_transcript = ' '.join(transcripts)
                
                # Fix CJK character spacing if needed
                if is_cjk:
                    # Remove spaces between CJK characters
                    cjk_pattern = r'([\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af])\s+([\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af])'
                    full_transcript = re.sub(cjk_pattern, r'\1\2', full_transcript)
                
                return full_transcript
            
            # Fallback to regular transcript if no utterances
            channels = results.get('channels', [])
            if channels and channels[0].get('alternatives'):
                transcript = channels[0]['alternatives'][0].get('transcript', '')
                
                # Fix CJK spacing in fallback too
                detected_lang = self._extract_language(response)
                if detected_lang in ['zh', 'zh-CN', 'zh-TW', 'zh-hans', 'zh-hant', 'ja', 'ko']:
                    cjk_pattern = r'([\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af])\s+([\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af])'
                    transcript = re.sub(cjk_pattern, r'\1\2', transcript)
                
                return transcript
            
            return ""
            
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
            # First check if language was detected in results
            results = response.get('results', {})
            channels = results.get('channels', [])
            if channels and len(channels) > 0:
                detected_languages = channels[0].get('detected_language')
                if detected_languages:
                    return detected_languages
            
            # Fall back to metadata
            metadata = response.get('metadata', {})
            return metadata.get('language', 'en')
        except Exception as e:
            logger.error(f"Error extracting language: {e}")
            return 'en'
    
    def _extract_sentiment(self, response: Dict[str, Any]) -> Optional[dict]:
        """Extract sentiment analysis from Deepgram response."""
        try:
            results = response.get('results', {})
            sentiments = results.get('sentiments')
            if sentiments:
                # Return the sentiment data structure as-is
                return sentiments
            return None
        except Exception as e:
            logger.error(f"Error extracting sentiment: {e}")
            return None
    
    def _extract_topics(self, response: Dict[str, Any]) -> Optional[dict]:
        """Extract topics from Deepgram response."""
        try:
            results = response.get('results', {})
            topics = results.get('topics')
            if topics:
                # Return the topics data structure as-is
                return topics
            return None
        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return None
    
    def _extract_intents(self, response: Dict[str, Any]) -> Optional[dict]:
        """Extract intents from Deepgram response."""
        try:
            results = response.get('results', {})
            intents = results.get('intents')
            if intents:
                # Return the intents data structure as-is
                return intents
            return None
        except Exception as e:
            logger.error(f"Error extracting intents: {e}")
            return None


# Singleton instance
_deepgram_service: Optional[DeepgramService] = None


def get_deepgram_service(api_key: Optional[str] = None) -> DeepgramService:
    """Get or create the singleton Deepgram service instance."""
    global _deepgram_service
    if _deepgram_service is None:
        _deepgram_service = DeepgramService(api_key)
    return _deepgram_service