"""
nirva_service - A Python-based distributed microservice system serving the 'nirva_app'.

This package provides:
- Models: Data models and schemas
- DB: Database access layers
- Services: Business logic and API services
- Config: Configuration management
- Prompts: Prompt templates
- Utils: Utility functions
"""

__version__ = "0.1.0"

from .config import *

# Import main models for easy access
from .models import *

__all__ = [
    "__version__",
]
