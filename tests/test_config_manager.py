"""Unit tests for Configuration Manager"""

import os
import pytest
import tempfile
from pathlib import Path

from src.config_manager import ConfigManager, ConfigurationError


class TestConfigManager:
    """Test suite for ConfigManager"""
    
    def test_load_default_config(self):
        """Test loading default configuration"""
        config = ConfigManager(config_dir="config", environment="dev")
        
        assert config.get("ingestion.batch_size") is not None
        assert config.get("validation.schema.strict_mode") is not None
        assert config.get("logging.level") is not None
    
    def test_environment_override(self):
        """Test environment-specific configuration overrides"""
        dev_config = ConfigManager(config_dir="config", environment="dev")
        prod_config = ConfigManager(config_dir="config", environment="prod")
        
        # Dev should have DEBUG logging
        assert dev_config.get("logging.level") == "DEBUG"
        
        # Prod should have WARNING logging
        assert prod_config.get("logging.level") == "WARNING"
    
    def test_get_with_dot_notation(self):
        """Test getting nested configuration values with dot notation"""
        config = ConfigManager(config_dir="config", environment="dev")
        
        batch_size = config.get("ingestion.batch_size")
        assert isinstance(batch_size, int)
        
        strict_mode = config.get("validation.schema.strict_mode")
        assert isinstance(strict_mode, bool)
    
    def test_get_with_default(self):
        """Test getting configuration with default value"""
        config = ConfigManager(config_dir="config", environment="dev")
        
        value = config.get("nonexistent.key", "default_value")
        assert value == "default_value"
    
    def test_get_all(self):
        """Test getting complete configuration"""
        config = ConfigManager(config_dir="config", environment="dev")
        
        all_config = config.get_all()
        assert isinstance(all_config, dict)
        assert "ingestion" in all_config
        assert "validation" in all_config
        assert "logging" in all_config
    
    def test_missing_config_file(self):
        """Test error handling for missing configuration file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ConfigurationError, match="Default configuration file not found"):
                ConfigManager(config_dir=tmpdir)
    
    def test_env_var_override(self, monkeypatch):
        """Test environment variable overrides for sensitive data"""
        monkeypatch.setenv("DB_PASSWORD", "test_password")
        monkeypatch.setenv("DB_USERNAME", "test_user")
        
        config = ConfigManager(config_dir="config", environment="dev")
        
        assert config.get("database.password") == "test_password"
        assert config.get("database.username") == "test_user"
    
    def test_validation_checks_required_keys(self):
        """Test that validation checks for required keys"""
        # This should work fine
        config = ConfigManager(config_dir="config", environment="dev")
        assert config.get("ingestion") is not None
