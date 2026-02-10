"""Configuration Management Module

Handles loading and managing configuration from YAML files
with environment-specific overrides.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or cannot be loaded"""
    pass


class ConfigManager:
    """Manages application configuration with environment-specific overrides"""
    
    def __init__(self, config_dir: str = "config", environment: Optional[str] = None):
        """Initialize configuration manager
        
        Args:
            config_dir: Directory containing configuration files
            environment: Environment name (dev, staging, prod). If None, uses ENV var
        """
        self.config_dir = Path(config_dir)
        self.environment = environment or os.getenv("ENVIRONMENT", "dev")
        self._config: Dict[str, Any] = {}
        
        # Load environment variables from .env file
        load_dotenv()
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from default and environment-specific files"""
        # Load default configuration
        default_config_path = self.config_dir / "default.yaml"
        if not default_config_path.exists():
            raise ConfigurationError(
                f"Default configuration file not found: {default_config_path}"
            )
        
        with open(default_config_path, 'r') as f:
            self._config = yaml.safe_load(f) or {}
        
        # Load environment-specific configuration
        env_config_path = self.config_dir / f"{self.environment}.yaml"
        if env_config_path.exists():
            with open(env_config_path, 'r') as f:
                env_config = yaml.safe_load(f) or {}
                self._config = self._merge_configs(self._config, env_config)
        
        # Override with environment variables for sensitive data
        self._apply_env_overrides()
        
        # Validate configuration
        self._validate_config()
    
    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """Recursively merge override config into base config
        
        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        merged = base.copy()
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides for sensitive configuration"""
        # Database credentials
        if "database" in self._config:
            db_config = self._config["database"]
            db_config["password"] = os.getenv("DB_PASSWORD", db_config.get("password", ""))
            db_config["username"] = os.getenv("DB_USERNAME", db_config.get("username", ""))
        
        # API keys
        if "api" in self._config:
            api_config = self._config["api"]
            api_config["api_key"] = os.getenv("API_KEY", api_config.get("api_key", ""))
    
    def _validate_config(self) -> None:
        """Validate that required configuration keys are present"""
        required_keys = ["ingestion", "validation", "logging"]
        missing_keys = [key for key in required_keys if key not in self._config]
        
        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration keys: {', '.join(missing_keys)}"
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration dictionary
        
        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()
    
    def reload(self) -> None:
        """Reload configuration from files"""
        self._config = {}
        self._load_config()
