"""
Enhanced Deepgram transcription service focused on word-level timestamps without diarization.
"""

import os
import json
from typing import Dict, Any, Optional, List
import aiohttp
from loguru import logger


class EnhancedDeepgramService:
    """Service for transcribing audio using Deepgram API with word-level timestamps."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Enhanced Deepgram service.

        Args:
            api_key: Deepgram API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            logger.warning("DEEPGRAM_API_KEY not configured")

        self.base_url = 'https://api.deepgram.com/v1/listen'

    async def transcribe_audio_with_words(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: str = 'en',  # Fixed language to avoid Portuguese misidentification
        model: str = 'nova-3'
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Deepgram API with word-level timestamps.

        Args:
            audio_bytes: Audio data in WAV format
            sample_rate: Sample rate of the audio
            language: Language code (fixed to prevent auto-detection issues)
            model: Deepgram model to use

        Returns:
            Dictionary containing transcription, word-level data, and metadata
        """
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not configured")

        # Build query parameters - OPTIMIZED FOR WORD-LEVEL TIMESTAMPS
        params = {
            'model': model,  # nova-3
            'language': language,  # Fixed language to avoid Portuguese misidentification
            'diarize': 'false',  # DISABLED - we use pyannote.ai for diarization
            'punctuate': 'true',  # Enable punctuation
            'utterances': 'true',  # Enable utterances for better segmentation
            'paragraphs': 'true',  # Group transcript into readable paragraphs
            'words': 'true',  # CRITICAL - Enable word-level data for timestamps
            'sentiment': 'true',  # Keep sentiment analysis
            'topics': 'true',  # Keep topic detection
            'intents': 'true',  # Keep intent recognition
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
                        word_level_data = self._extract_word_level_data(result)
                        sentiment_data = self._extract_sentiment(result)
                        topics_data = self._extract_topics(result)
                        intents_data = self._extract_intents(result)

                        logger.info(
                            f"Transcription successful: {len(transcription)} chars, "
                            f"confidence: {confidence:.2f}, language: {detected_language}, "
                            f"words: {len(word_level_data)}"
                        )

                        return {
                            'transcription': transcription,
                            'confidence': confidence,
                            'language': detected_language,
                            'words': word_level_data,  # Word-level timestamps
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
        """Extract transcription text from Deepgram response (without speaker labels)."""
        import re

        try:
            results = response.get('results', {})

            # Use utterances for better formatting (but without speaker info)
            utterances = results.get('utterances', [])
            if utterances:
                # Get language for proper spacing
                detected_lang = self._extract_language(response)
                is_cjk = detected_lang in ['zh', 'zh-CN', 'zh-TW', 'zh-hans', 'zh-hant', 'ja', 'ko']

                # Build transcript from utterances (no speaker labels)
                transcripts = []

                for utt in utterances:
                    text = utt.get('transcript', '').strip()
                    if text:
                        transcripts.append(text)

                # Join with appropriate spacing
                if is_cjk:
                    # For CJK, join without extra spaces
                    full_transcript = ''.join(transcripts)
                else:
                    # For non-CJK, join with space
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

    def _extract_word_level_data(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract word-level timestamp data from Deepgram response.

        Returns:
            List of word objects: [{"word": "hello", "start": 1.2, "end": 1.5}, ...]
        """
        try:
            results = response.get('results', {})
            channels = results.get('channels', [])

            if not channels:
                return []

            channel = channels[0]
            alternatives = channel.get('alternatives', [])

            if not alternatives:
                return []

            alternative = alternatives[0]
            words = alternative.get('words', [])

            word_data = []
            for word_obj in words:
                word_text = word_obj.get('word', '')
                start_time = word_obj.get('start', 0.0)
                end_time = word_obj.get('end', 0.0)
                confidence = word_obj.get('confidence', 0.0)

                if word_text:  # Only include words with text
                    word_data.append({
                        'word': word_text,
                        'start': float(start_time),
                        'end': float(end_time),
                        'confidence': float(confidence)
                    })

            logger.debug(f"Extracted {len(word_data)} word-level timestamps")
            return word_data

        except Exception as e:
            logger.error(f"Error extracting word-level data: {e}")
            return []

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
                return intents
            return None
        except Exception as e:
            logger.error(f"Error extracting intents: {e}")
            return None


# Singleton instance
_enhanced_deepgram_service: Optional[EnhancedDeepgramService] = None


def get_enhanced_deepgram_service(api_key: Optional[str] = None) -> EnhancedDeepgramService:
    """Get or create the singleton Enhanced Deepgram service instance."""
    global _enhanced_deepgram_service
    if _enhanced_deepgram_service is None:
        _enhanced_deepgram_service = EnhancedDeepgramService(api_key)
    return _enhanced_deepgram_service