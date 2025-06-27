"""Basic tests for the nirva_service package."""

import sys
from pathlib import Path

import pytest

# Add src directory to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from nirva_service import __version__


def test_version():
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_package_import():
    """Test that package imports correctly."""
    import nirva_service

    assert nirva_service is not None


def test_config_import():
    """Test that config modules import correctly."""
    from nirva_service.config import (
        AnalyzerServerConfig,
        AppserviceServerConfig,
        ChatServerConfig,
    )

    # Test that config classes can be instantiated
    app_config = AppserviceServerConfig()
    chat_config = ChatServerConfig()
    analyzer_config = AnalyzerServerConfig()

    assert app_config.server_port == 8001
    assert chat_config.port == 8500
    assert analyzer_config.port == 8600


def test_models_import():
    """Test that model modules import correctly."""
    from nirva_service.models import ChatMessage, JournalFile

    # Test basic model functionality
    assert ChatMessage is not None
    assert JournalFile is not None
