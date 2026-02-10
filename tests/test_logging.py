"""Unit tests for Logging Configuration Module"""

import pytest
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch

from src.logging_config import LoggerSetup, ErrorTracker, setup_pipeline_logger
from src.config_manager import ConfigManager


@pytest.fixture
def config():
    """Fixture providing configuration manager"""
    return ConfigManager(config_dir="config", environment="dev")


class TestLoggerSetup:
    """Test suite for LoggerSetup"""
    
    def test_setup_logging(self, config):
        """Test logger setup with configuration"""
        logger = LoggerSetup.setup_logging(config, "test_logger")
        
        assert logger is not None
        assert logger.name == "test_logger"
        assert len(logger.handlers) >= 1  # At least console handler
    
    def test_logger_level_from_config(self, config):
        """Test that logger uses level from config"""
        logger = LoggerSetup.setup_logging(config, "test_level")
        
        # Dev config should have DEBUG level
        assert logger.level == logging.DEBUG
    
    def test_console_handler_enabled(self, config):
        """Test console handler is added when enabled"""
        logger = LoggerSetup.setup_logging(config, "test_console")
        
        console_handlers = [
            h for h in logger.handlers 
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        
        assert len(console_handlers) > 0
    
    def test_file_handler_enabled(self, config):
        """Test file handler is added when enabled"""
        logger = LoggerSetup.setup_logging(config, "test_file")
        
        file_handlers = [
            h for h in logger.handlers 
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        
        assert len(file_handlers) > 0
    
    def test_get_existing_logger(self, config):
        """Test retrieving existing logger"""
        logger1 = LoggerSetup.setup_logging(config, "test_existing")
        logger2 = LoggerSetup.get_logger("test_existing")
        
        assert logger1 is logger2
    
    def test_setup_pipeline_logger(self, config):
        """Test convenience function"""
        logger = setup_pipeline_logger(config)
        
        assert logger is not None
        assert logger.name == "pipeline"


class TestErrorTracker:
    """Test suite for ErrorTracker"""
    
    def test_log_error(self):
        """Test logging an error"""
        tracker = ErrorTracker()
        
        error = ValueError("Test error")
        tracker.log_error(error, "test_context", {"id": 1})
        
        assert len(tracker.errors) == 1
        assert tracker.errors[0]["error_type"] == "ValueError"
        assert tracker.errors[0]["context"] == "test_context"
    
    def test_log_warning(self):
        """Test logging a warning"""
        tracker = ErrorTracker()
        
        tracker.log_warning("Test warning", "test_context")
        
        assert len(tracker.warnings) == 1
        assert tracker.warnings[0]["message"] == "Test warning"
    
    def test_quarantine_record(self):
        """Test quarantining a failed record"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ErrorTracker()
            tracker.quarantine_path = Path(tmpdir)
            
            record = {"id": 1, "name": "Test", "_source": "csv"}
            tracker.quarantine_record(record, "Invalid data")
            
            # Check that file was created
            files = list(Path(tmpdir).glob("*.json"))
            assert len(files) == 1
    
    def test_get_error_summary(self):
        """Test getting error summary"""
        tracker = ErrorTracker()
        
        tracker.log_error(ValueError("Error 1"), "context1")
        tracker.log_error(ValueError("Error 2"), "context2")
        tracker.log_error(TypeError("Error 3"), "context3")
        tracker.log_warning("Warning 1", "context4")
        
        summary = tracker.get_error_summary()
        
        assert summary["total_errors"] == 3
        assert summary["total_warnings"] == 1
        assert "ValueError" in summary["error_types"]
        assert summary["error_types"]["ValueError"] == 2
        assert summary["error_types"]["TypeError"] == 1
    
    def test_clear_errors(self):
        """Test clearing errors and warnings"""
        tracker = ErrorTracker()
        
        tracker.log_error(ValueError("Error"), "context")
        tracker.log_warning("Warning", "context")
        
        assert len(tracker.errors) == 1
        assert len(tracker.warnings) == 1
        
        tracker.clear()
        
        assert len(tracker.errors) == 0
        assert len(tracker.warnings) == 0
    
    def test_multiple_errors_different_types(self):
        """Test tracking multiple error types"""
        tracker = ErrorTracker()
        
        tracker.log_error(ValueError("Value error"), "context1")
        tracker.log_error(KeyError("Key error"), "context2")
        tracker.log_error(ValueError("Another value error"), "context3")
        
        summary = tracker.get_error_summary()
        
        assert summary["total_errors"] == 3
        assert len(summary["error_types"]) == 2
        assert summary["error_types"]["ValueError"] == 2
        assert summary["error_types"]["KeyError"] == 1
