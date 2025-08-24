"""
Storage services for nirva_service.
"""

from .aws_sts_service import STSService, get_sts_service

__all__ = [
    "STSService",
    "get_sts_service",
]