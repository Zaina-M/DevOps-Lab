"""Pytest configuration and shared fixtures"""

import os
import sys
from pathlib import Path
import pytest

# Get project root directory (parent of tests directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Add src to Python path
sys.path.insert(0, str(PROJECT_ROOT))

# Change working directory to project root for tests
os.chdir(PROJECT_ROOT)


@pytest.fixture
def project_root():
    """Fixture providing project root path"""
    return PROJECT_ROOT


@pytest.fixture
def config_dir():
    """Fixture providing config directory path"""
    return PROJECT_ROOT / "config"


@pytest.fixture
def data_dir():
    """Fixture providing data directory path"""
    return PROJECT_ROOT / "data"


@pytest.fixture
def schemas_dir():
    """Fixture providing schemas directory path"""
    return PROJECT_ROOT / "schemas"
