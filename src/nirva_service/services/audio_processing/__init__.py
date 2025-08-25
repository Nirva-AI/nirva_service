"""Audio processing services."""

from .vad_service import VADService, get_vad_service

__all__ = ["VADService", "get_vad_service"]