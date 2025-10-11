"""
Diarization merger service that combines pyannote.ai speaker segments with Deepgram word timestamps
to create sentence-level speaker-aware transcription output.
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger


class DiarizationMerger:
    """Merges speaker diarization with word-level transcription data."""

    def __init__(self, sentence_gap_seconds: float = 1.0):
        """
        Initialize the diarization merger.

        Args:
            sentence_gap_seconds: Gap between words to consider as sentence boundary
        """
        self.sentence_gap_seconds = sentence_gap_seconds

    def merge_diarization_with_words(
        self,
        speaker_segments: List[Dict[str, Any]],
        word_data: List[Dict[str, Any]],
        base_datetime: Optional[datetime] = None,
        timezone_offset_seconds: Optional[int] = None
    ) -> str:
        """
        Merge speaker diarization with word-level timestamps to create sentence-level output.

        Args:
            speaker_segments: List of speaker segments from pyannote.ai
                Format: [{"speaker": "0", "start": 1.2, "end": 3.4}, ...]
            word_data: List of word timestamps from Deepgram
                Format: [{"word": "hello", "start": 1.2, "end": 1.5}, ...]
            base_datetime: Base datetime for timestamp calculation (defaults to now)

        Returns:
            Formatted transcription text with timestamps and speakers:
            "[HH:MM:SS-HH:MM:SS] Speaker 0: Hello there. [HH:MM:SS-HH:MM:SS] Speaker 1: How are you?"
        """
        if not word_data:
            logger.warning("No word data provided for diarization merge")
            return ""

        if not speaker_segments:
            logger.warning("No speaker segments provided, creating single-speaker output")
            return self._create_single_speaker_output(word_data, base_datetime, timezone_offset_seconds)

        # Step 1: Assign speakers to words
        speaker_words = self._assign_speakers_to_words(speaker_segments, word_data)

        # Step 2: Group words into sentences by speaker
        speaker_sentences = self._group_words_into_sentences(speaker_words)

        # Step 3: Format output with timestamps
        return self._format_output_with_timestamps(speaker_sentences, base_datetime, timezone_offset_seconds)

    def _assign_speakers_to_words(
        self,
        speaker_segments: List[Dict[str, Any]],
        word_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Assign speaker IDs to words based on timestamp overlap.

        Returns:
            List of words with speaker assignments:
            [{"word": "hello", "start": 1.2, "end": 1.5, "speaker": "0"}, ...]
        """
        speaker_words = []

        for word in word_data:
            word_start = word['start']
            word_end = word['end']
            word_midpoint = (word_start + word_end) / 2

            # Find the speaker segment that contains this word
            assigned_speaker = None
            best_overlap = 0

            for segment in speaker_segments:
                seg_start = segment['start']
                seg_end = segment['end']

                # Check if word overlaps with this speaker segment
                overlap_start = max(word_start, seg_start)
                overlap_end = min(word_end, seg_end)
                overlap_duration = max(0, overlap_end - overlap_start)

                # Use the segment with the most overlap, or containing the midpoint
                if overlap_duration > 0:
                    if (overlap_duration > best_overlap or
                        (seg_start <= word_midpoint <= seg_end)):
                        assigned_speaker = segment['speaker']
                        best_overlap = overlap_duration

            # If no overlap found, assign to closest speaker by midpoint
            if assigned_speaker is None:
                min_distance = float('inf')
                for segment in speaker_segments:
                    seg_start = segment['start']
                    seg_end = segment['end']
                    seg_midpoint = (seg_start + seg_end) / 2

                    distance = abs(word_midpoint - seg_midpoint)
                    if distance < min_distance:
                        min_distance = distance
                        assigned_speaker = segment['speaker']

            # Default to speaker "0" if still no assignment
            if assigned_speaker is None:
                assigned_speaker = "0"

            speaker_words.append({
                'word': word['word'],
                'start': word['start'],
                'end': word['end'],
                'confidence': word.get('confidence', 0.0),
                'speaker': assigned_speaker
            })

        logger.info(f"Assigned speakers to {len(speaker_words)} words")
        return speaker_words

    def _group_words_into_sentences(
        self,
        speaker_words: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Group consecutive words from the same speaker into sentences.

        Returns:
            List of sentences with speaker and timing info:
            [{"speaker": "0", "sentence": "Hello there", "start": 1.2, "end": 3.4}, ...]
        """
        if not speaker_words:
            return []

        sentences = []
        current_sentence = {
            'speaker': speaker_words[0]['speaker'],
            'words': [speaker_words[0]['word']],
            'start': speaker_words[0]['start'],
            'end': speaker_words[0]['end']
        }

        for i in range(1, len(speaker_words)):
            word = speaker_words[i]
            prev_word = speaker_words[i-1]

            # Check if we should start a new sentence
            speaker_changed = word['speaker'] != current_sentence['speaker']
            time_gap = word['start'] - prev_word['end']
            large_gap = time_gap > self.sentence_gap_seconds

            # Check for sentence-ending punctuation
            prev_word_text = prev_word['word'].strip()
            has_sentence_end = prev_word_text.endswith(('.', '!', '?', '。', '！', '？'))

            if speaker_changed or (large_gap and has_sentence_end):
                # Finalize current sentence
                sentence_text = ' '.join(current_sentence['words'])
                sentence_text = self._clean_sentence_text(sentence_text)

                if sentence_text.strip():  # Only add non-empty sentences
                    sentences.append({
                        'speaker': current_sentence['speaker'],
                        'sentence': sentence_text,
                        'start': current_sentence['start'],
                        'end': current_sentence['end']
                    })

                # Start new sentence
                current_sentence = {
                    'speaker': word['speaker'],
                    'words': [word['word']],
                    'start': word['start'],
                    'end': word['end']
                }
            else:
                # Continue current sentence
                current_sentence['words'].append(word['word'])
                current_sentence['end'] = word['end']  # Extend end time

        # Don't forget the last sentence
        if current_sentence['words']:
            sentence_text = ' '.join(current_sentence['words'])
            sentence_text = self._clean_sentence_text(sentence_text)

            if sentence_text.strip():
                sentences.append({
                    'speaker': current_sentence['speaker'],
                    'sentence': sentence_text,
                    'start': current_sentence['start'],
                    'end': current_sentence['end']
                })

        logger.info(f"Grouped {len(speaker_words)} words into {len(sentences)} sentences")
        return sentences

    def _clean_sentence_text(self, text: str) -> str:
        """Clean up sentence text (fix spacing, punctuation, etc.)."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Fix spacing around punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)  # Ensure space after sentence endings

        return text

    def _format_output_with_timestamps(
        self,
        sentences: List[Dict[str, Any]],
        base_datetime: Optional[datetime] = None,
        timezone_offset_seconds: Optional[int] = None
    ) -> str:
        """
        Format sentences into the required output format with HH:MM:SS timestamps.

        Args:
            sentences: List of sentence objects
            base_datetime: Base datetime for timestamp calculation
            timezone_offset_seconds: Timezone offset in seconds from UTC

        Returns:
            Formatted string: "[HH:MM:SS-HH:MM:SS] 0: Hello. [HH:MM:SS-HH:MM:SS] 1: Hi."
        """
        if not sentences:
            return ""

        if base_datetime is None:
            base_datetime = datetime.now()

        # Apply timezone offset from metadata (if available)
        if timezone_offset_seconds is not None:
            timezone_offset = timedelta(seconds=timezone_offset_seconds)
        else:
            # Default to UTC if no offset provided
            timezone_offset = timedelta(0)
            logger.warning("No timezone offset provided, using UTC")

        formatted_parts = []

        for sentence in sentences:
            # Convert seconds to HH:MM:SS format with timezone adjustment
            start_time = base_datetime + timedelta(seconds=sentence['start']) + timezone_offset
            end_time = base_datetime + timedelta(seconds=sentence['end']) + timezone_offset

            start_str = start_time.strftime("%H:%M:%S")
            end_str = end_time.strftime("%H:%M:%S")

            # Use speaker ID exactly as provided by the API
            speaker_id = sentence['speaker']

            # Format: [HH:MM:SS-HH:MM:SS] speaker_id: sentence text
            formatted_part = f"[{start_str}-{end_str}] {speaker_id}: {sentence['sentence']}"
            formatted_parts.append(formatted_part)

        result = " ".join(formatted_parts)
        logger.info(f"Formatted {len(sentences)} sentences into timestamped output")
        return result

    def _create_single_speaker_output(
        self,
        word_data: List[Dict[str, Any]],
        base_datetime: Optional[datetime] = None,
        timezone_offset_seconds: Optional[int] = None
    ) -> str:
        """
        Create output for single speaker (no diarization data).

        Args:
            word_data: List of word timestamps
            base_datetime: Base datetime for timestamp calculation

        Returns:
            Formatted string with single speaker
        """
        if not word_data:
            return ""

        if base_datetime is None:
            base_datetime = datetime.now()

        # Group all words into sentences based on timing gaps and punctuation
        sentences = []
        current_words = [word_data[0]['word']]
        start_time = word_data[0]['start']
        end_time = word_data[0]['end']

        for i in range(1, len(word_data)):
            word = word_data[i]
            prev_word = word_data[i-1]

            time_gap = word['start'] - prev_word['end']
            prev_word_text = prev_word['word'].strip()
            has_sentence_end = prev_word_text.endswith(('.', '!', '?', '。', '！', '？'))

            if time_gap > self.sentence_gap_seconds and has_sentence_end:
                # End current sentence
                sentence_text = ' '.join(current_words)
                sentence_text = self._clean_sentence_text(sentence_text)

                if sentence_text.strip():
                    sentences.append({
                        'sentence': sentence_text,
                        'start': start_time,
                        'end': end_time
                    })

                # Start new sentence
                current_words = [word['word']]
                start_time = word['start']
                end_time = word['end']
            else:
                # Continue current sentence
                current_words.append(word['word'])
                end_time = word['end']

        # Don't forget the last sentence
        if current_words:
            sentence_text = ' '.join(current_words)
            sentence_text = self._clean_sentence_text(sentence_text)

            if sentence_text.strip():
                sentences.append({
                    'sentence': sentence_text,
                    'start': start_time,
                    'end': end_time
                })

        # Format with default speaker "0"
        formatted_parts = []
        for sentence in sentences:
            start_time = base_datetime + timedelta(seconds=sentence['start'])
            end_time = base_datetime + timedelta(seconds=sentence['end'])

            start_str = start_time.strftime("%H:%M:%S")
            end_str = end_time.strftime("%H:%M:%S")

            # Apply timezone offset from metadata (if available)
            if timezone_offset_seconds is not None:
                timezone_offset = timedelta(seconds=timezone_offset_seconds)
            else:
                timezone_offset = timedelta(0)

            start_time = start_time + timezone_offset
            end_time = end_time + timezone_offset

            start_str = start_time.strftime("%H:%M:%S")
            end_str = end_time.strftime("%H:%M:%S")

            # Use default speaker ID as provided by API (usually "0" for single speaker)
            formatted_part = f"[{start_str}-{end_str}] 0: {sentence['sentence']}"
            formatted_parts.append(formatted_part)

        result = " ".join(formatted_parts)
        logger.info(f"Created single-speaker output with {len(sentences)} sentences")
        return result


# Singleton instance
_diarization_merger: Optional[DiarizationMerger] = None


def get_diarization_merger() -> DiarizationMerger:
    """Get or create the singleton DiarizationMerger instance."""
    global _diarization_merger
    if _diarization_merger is None:
        _diarization_merger = DiarizationMerger()
    return _diarization_merger