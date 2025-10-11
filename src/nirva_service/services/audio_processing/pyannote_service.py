"""
Pyannote.ai diarization service for superior speaker diarization.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
import aiohttp
from loguru import logger


class PyannoteService:
    """Service for speaker diarization using Pyannote.ai API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Pyannote service.

        Args:
            api_key: Pyannote API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv('PYANNOTE_API_KEY')
        if not self.api_key:
            logger.warning("PYANNOTE_API_KEY not configured")

        self.base_url = os.getenv('PYANNOTE_BASE_URL', 'https://api.pyannote.ai/v1')
        self.polling_interval = int(os.getenv('DIARIZATION_POLLING_INTERVAL', '10'))

    async def diarize_audio_url(
        self,
        audio_url: str,
        model: str = 'precision-1',
        max_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform speaker diarization on audio from URL.

        Args:
            audio_url: Public URL to audio file
            model: Diarization model to use
            max_speakers: Maximum number of speakers
            min_speakers: Minimum number of speakers

        Returns:
            List of speaker segments: [{"speaker": "0", "start": 1.2, "end": 3.4}, ...]
        """
        if not self.api_key:
            raise ValueError("PYANNOTE_API_KEY not configured")

        # Submit diarization job
        job_id = await self._submit_diarization_job(
            audio_url, model, max_speakers, min_speakers
        )

        # Poll for completion
        results = await self._poll_job_completion(job_id)

        # Parse and return diarization segments
        return self._parse_diarization_results(results)

    async def _submit_diarization_job(
        self,
        audio_url: str,
        model: str,
        max_speakers: Optional[int],
        min_speakers: Optional[int]
    ) -> str:
        """
        Submit diarization job to Pyannote API.

        Returns:
            Job ID for polling
        """
        url = f"{self.base_url}/diarize"

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'url': audio_url,
            'model': model
        }

        # Add optional speaker constraints
        if max_speakers is not None:
            payload['maxSpeakers'] = max_speakers
        if min_speakers is not None:
            payload['minSpeakers'] = min_speakers

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        job_id = result.get('jobId')
                        if not job_id:
                            raise ValueError("No jobId returned from Pyannote API")

                        logger.info(f"Diarization job submitted: {job_id}")
                        return job_id
                    else:
                        error_text = await response.text()
                        logger.error(f"Pyannote API error {response.status}: {error_text}")
                        raise Exception(f"Pyannote API error {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            logger.error(f"Network error calling Pyannote API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error submitting diarization job: {e}")
            raise

    async def _poll_job_completion(self, job_id: str, max_wait_seconds: int = 600) -> Dict[str, Any]:
        """
        Poll job status until completion.

        Args:
            job_id: Job ID to poll
            max_wait_seconds: Maximum time to wait for completion

        Returns:
            Job results when completed
        """
        url = f"{self.base_url}/jobs/{job_id}"

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        start_time = asyncio.get_event_loop().time()

        async with aiohttp.ClientSession() as session:
            while True:
                # Check if we've exceeded max wait time
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_wait_seconds:
                    raise TimeoutError(f"Diarization job {job_id} timed out after {max_wait_seconds}s")

                try:
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            status = result.get('status')

                            logger.debug(f"Job {job_id} status: {status}")

                            if status == 'succeeded':
                                logger.info(f"Diarization job {job_id} completed successfully")
                                return result
                            elif status in ['failed', 'canceled']:
                                error_msg = result.get('error', 'Unknown error')
                                logger.error(f"Diarization job {job_id} {status}: {error_msg}")
                                logger.error(f"Full API response: {result}")
                                raise Exception(f"Diarization job {status}: {error_msg}")
                            elif status in ['pending', 'created', 'running']:
                                # Job still in progress, continue polling
                                await asyncio.sleep(self.polling_interval)
                                continue
                            else:
                                logger.warning(f"Unknown job status: {status}")
                                await asyncio.sleep(self.polling_interval)
                                continue
                        else:
                            error_text = await response.text()
                            logger.error(f"Error polling job {job_id}: {response.status} {error_text}")
                            raise Exception(f"Error polling job: {response.status} {error_text}")

                except aiohttp.ClientError as e:
                    logger.warning(f"Network error polling job {job_id}: {e}, retrying...")
                    await asyncio.sleep(self.polling_interval)
                    continue
                except Exception as e:
                    logger.error(f"Error polling job {job_id}: {e}")
                    raise

    def _parse_diarization_results(self, job_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse diarization results from Pyannote API response.

        Args:
            job_result: Complete job result from API

        Returns:
            List of speaker segments with normalized format
        """
        logger.debug(f"Parsing job result: {json.dumps(job_result, indent=2)}")

        try:
            # Extract the output field which contains the actual diarization
            output = job_result.get('output')
            if not output:
                logger.warning("No output field in diarization results")
                return []

            # The output should contain speaker segments
            # Expected format varies, but typically includes speaker timeline data
            segments = []

            # Handle different possible output formats from Pyannote API
            if isinstance(output, list):
                # Format: [{"speaker": "0", "start": 1.2, "end": 3.4}, ...]
                for segment in output:
                    if all(key in segment for key in ['speaker', 'start', 'end']):
                        segments.append({
                            'speaker': str(segment['speaker']),
                            'start': float(segment['start']),
                            'end': float(segment['end'])
                        })
            elif isinstance(output, dict):
                # Handle object-based format
                if 'diarization' in output:
                    # This is the actual pyannote.ai format
                    for segment in output['diarization']:
                        if all(key in segment for key in ['speaker', 'start', 'end']):
                            segments.append({
                                'speaker': str(segment['speaker']),
                                'start': float(segment['start']),
                                'end': float(segment['end'])
                            })
                elif 'segments' in output:
                    for segment in output['segments']:
                        if all(key in segment for key in ['speaker', 'start', 'end']):
                            segments.append({
                                'speaker': str(segment['speaker']),
                                'start': float(segment['start']),
                                'end': float(segment['end'])
                            })
                # Handle timeline format
                elif 'timeline' in output:
                    timeline = output['timeline']
                    for entry in timeline:
                        if all(key in entry for key in ['speaker', 'start', 'end']):
                            segments.append({
                                'speaker': str(entry['speaker']),
                                'start': float(entry['start']),
                                'end': float(entry['end'])
                            })

            # Sort segments by start time
            segments.sort(key=lambda x: x['start'])

            logger.info(f"Parsed {len(segments)} speaker segments from diarization results")

            return segments

        except Exception as e:
            logger.error(f"Error parsing diarization results: {e}")
            logger.error(f"Failed to parse diarization results")
            logger.error(f"Raw job result: {json.dumps(job_result, indent=2)}")
            return []


# Singleton instance
_pyannote_service: Optional[PyannoteService] = None


def get_pyannote_service(api_key: Optional[str] = None) -> PyannoteService:
    """Get or create the singleton Pyannote service instance."""
    global _pyannote_service
    if _pyannote_service is None:
        _pyannote_service = PyannoteService(api_key)
    return _pyannote_service