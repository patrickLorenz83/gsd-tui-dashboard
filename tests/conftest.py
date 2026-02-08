"""Pytest configuration and shared fixtures."""
import pytest
from pathlib import Path
import sys

# Add parent directory to path so we can import parsers
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers import GSDParser


@pytest.fixture
def parser(tmp_path):
    """Creates a GSDParser instance with a temporary planning directory."""
    planning = tmp_path / ".planning"
    planning.mkdir()
    return GSDParser(tmp_path)
