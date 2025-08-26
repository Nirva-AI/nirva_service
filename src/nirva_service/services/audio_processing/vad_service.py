"""
Voice Activity Detection (VAD) service using Silero VAD v4.
Detects speech segments in audio files.
"""

import os
import tempfile
import warnings
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import numpy as np
import soundfile as sf
from loguru import logger
import torch
import torchaudio
from silero_vad import load_silero_vad, get_speech_timestamps, save_audio, read_audio

# Suppress ONNX warnings about unused initializers
warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")


class VADService:
    """Service for detecting speech segments in audio files using Silero VAD."""
    
    def __init__(self, use_onnx: bool = True):
        """
        Initialize VAD service with Silero VAD model.
        
        Args:
            use_onnx: Use ONNX runtime for better CPU performance
        """
        self.use_onnx = use_onnx
        self.model = None
        self.sample_rate = 16000  # Silero VAD works with 16kHz
        self._load_model()
    
    def _load_model(self):
        """Load Silero VAD model."""
        try:
            logger.info(f"Loading Silero VAD model (ONNX: {self.use_onnx})")
            
            # Set ONNX runtime to only show errors
            if self.use_onnx:
                import onnxruntime as ort
                ort.set_default_logger_severity(3)  # ERROR level only
            
            self.model = load_silero_vad(onnx=self.use_onnx)
            logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD model: {e}")
            raise
    
    def process_audio_file(
        self, 
        audio_path: str,
        return_seconds: bool = True,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        threshold: float = 0.5,
        speech_pad_ms: int = 30
    ) -> Dict[str, Any]:
        """
        Process an audio file and detect speech segments.
        
        Args:
            audio_path: Path to the audio file
            return_seconds: Return timestamps in seconds (vs samples)
            min_speech_duration_ms: Minimum speech chunk duration
            min_silence_duration_ms: Minimum silence duration to split speech
            threshold: Speech detection threshold (0.0-1.0)
            speech_pad_ms: Padding to add to speech segments
            
        Returns:
            Dictionary containing:
                - segments: List of [start, end] timestamps
                - total_duration: Total audio duration in seconds
                - speech_duration: Total speech duration in seconds
                - num_segments: Number of speech segments
                - speech_ratio: Ratio of speech to total duration
        """
        try:
            # Read audio file
            logger.info(f"Processing audio file: {audio_path}")
            wav = read_audio(audio_path, sampling_rate=self.sample_rate)
            
            # Get total duration
            total_duration = len(wav) / self.sample_rate
            
            # Detect speech timestamps
            speech_timestamps = get_speech_timestamps(
                wav,
                self.model,
                sampling_rate=self.sample_rate,
                threshold=threshold,
                min_speech_duration_ms=min_speech_duration_ms,
                min_silence_duration_ms=min_silence_duration_ms,
                speech_pad_ms=speech_pad_ms,
                return_seconds=return_seconds
            )
            
            # Convert to simple list format
            segments = []
            speech_duration = 0.0
            
            for segment in speech_timestamps:
                start = segment['start']
                end = segment['end']
                segments.append([start, end])
                
                if return_seconds:
                    speech_duration += (end - start)
                else:
                    speech_duration += (end - start) / self.sample_rate
            
            # Calculate speech ratio
            speech_ratio = speech_duration / total_duration if total_duration > 0 else 0
            
            result = {
                'segments': segments,
                'total_duration': total_duration,
                'speech_duration': speech_duration,
                'num_segments': len(segments),
                'speech_ratio': speech_ratio
            }
            
            logger.info(
                f"VAD complete: {len(segments)} segments, "
                f"{speech_duration:.1f}s speech out of {total_duration:.1f}s total "
                f"({speech_ratio*100:.1f}% speech)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio file {audio_path}: {e}")
            raise
    
    def process_audio_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        return_seconds: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process audio from bytes data.
        
        Args:
            audio_bytes: Raw audio bytes
            sample_rate: Sample rate of the audio
            return_seconds: Return timestamps in seconds
            **kwargs: Additional arguments for VAD processing
            
        Returns:
            Same as process_audio_file
        """
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            temp_path = tmp_file.name
            
        try:
            # Write audio bytes to temp file
            with open(temp_path, 'wb') as f:
                f.write(audio_bytes)
            
            # Process the temp file
            return self.process_audio_file(temp_path, return_seconds=return_seconds, **kwargs)
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def extract_and_concat_speech(
        self,
        audio_files_with_vad: List[Tuple[str, Dict[str, Any]]],
        output_sample_rate: int = 16000
    ) -> Optional[bytes]:
        """
        Extract and concatenate speech segments from multiple audio files.
        
        Args:
            audio_files_with_vad: List of tuples (audio_path, vad_result)
            output_sample_rate: Sample rate for output audio
            
        Returns:
            Concatenated speech audio as WAV bytes, or None if no speech
        """
        try:
            all_speech_segments = []
            
            for audio_path, vad_result in audio_files_with_vad:
                if not vad_result.get('segments'):
                    logger.debug(f"No speech in {audio_path}, skipping")
                    continue
                
                # Read audio file
                wav = read_audio(audio_path, sampling_rate=self.sample_rate)
                
                # Extract speech segments (vad_result segments are in samples if return_seconds=False)
                for start, end in vad_result['segments']:
                    # If segments are in seconds, convert to samples
                    if isinstance(start, float):
                        start_sample = int(start * self.sample_rate)
                        end_sample = int(end * self.sample_rate)
                    else:
                        start_sample = start
                        end_sample = end
                    
                    speech_segment = wav[start_sample:end_sample]
                    all_speech_segments.append(speech_segment)
            
            if not all_speech_segments:
                logger.warning("No speech segments found in any audio files")
                return None
            
            # Concatenate all speech segments
            concatenated = torch.cat(all_speech_segments)
            
            # Convert to numpy for saving
            audio_numpy = concatenated.numpy()
            
            # Save to temporary WAV file and read back as bytes
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                # Save using soundfile for proper WAV format
                import soundfile as sf
                sf.write(temp_path, audio_numpy, output_sample_rate)
                
                # Read back as bytes
                with open(temp_path, 'rb') as f:
                    wav_bytes = f.read()
                
                total_duration = len(concatenated) / self.sample_rate
                logger.info(f"Extracted {total_duration:.1f}s of speech from {len(audio_files_with_vad)} files")
                
                return wav_bytes
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.error(f"Error extracting and concatenating speech: {e}")
            return None
    
    def filter_silence(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        **vad_kwargs
    ) -> Optional[str]:
        """
        Remove silence from audio file, keeping only speech segments.
        
        Args:
            audio_path: Input audio file path
            output_path: Output file path (optional, auto-generated if not provided)
            **vad_kwargs: VAD processing parameters
            
        Returns:
            Path to the filtered audio file, or None if no speech detected
        """
        try:
            # Get speech segments
            vad_result = self.process_audio_file(audio_path, return_seconds=False, **vad_kwargs)
            
            if not vad_result['segments']:
                logger.warning(f"No speech detected in {audio_path}")
                return None
            
            # Read original audio
            wav = read_audio(audio_path, sampling_rate=self.sample_rate)
            
            # Extract speech segments
            speech_audio = []
            for start, end in vad_result['segments']:
                speech_audio.append(wav[start:end])
            
            # Concatenate all speech segments
            filtered_wav = torch.cat(speech_audio)
            
            # Generate output path if not provided
            if output_path is None:
                base_name = Path(audio_path).stem
                output_path = f"{base_name}_speech_only.wav"
            
            # Save filtered audio
            save_audio(output_path, filtered_wav, sampling_rate=self.sample_rate)
            
            logger.info(f"Filtered audio saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error filtering silence from {audio_path}: {e}")
            raise


# Singleton instance
_vad_service: Optional[VADService] = None


def get_vad_service(use_onnx: bool = True) -> VADService:
    """Get or create the singleton VAD service instance."""
    global _vad_service
    if _vad_service is None:
        _vad_service = VADService(use_onnx=use_onnx)
    return _vad_service