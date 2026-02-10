"""Logging Configuration Module

Provides structured logging setup with file rotation,
console output, and different log levels per environment.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.config_manager import ConfigManager


class LoggerSetup:
    """Configure and manage application logging"""
    
    _loggers = {}
    
    @classmethod
    def setup_logging(cls, config: ConfigManager, name: str = "pipeline") -> logging.Logger:
        """Setup logger with configuration
        
        Args:
            config: Configuration manager instance
            name: Logger name
            
        Returns:
            Configured logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(cls._get_log_level(config))
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Setup console handler
        if config.get("logging.console.enabled", True):
            console_handler = cls._create_console_handler(config)
            logger.addHandler(console_handler)
        
        # Setup file handler
        if config.get("logging.file.enabled", True):
            file_handler = cls._create_file_handler(config)
            logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def _get_log_level(cls, config: ConfigManager) -> int:
        """Get logging level from config
        
        Args:
            config: Configuration manager
            
        Returns:
            Logging level constant
        """
        level_name = config.get("logging.level", "INFO").upper()
        return getattr(logging, level_name, logging.INFO)
    
    @classmethod
    def _create_console_handler(cls, config: ConfigManager) -> logging.StreamHandler:
        """Create console handler with formatting
        
        Args:
            config: Configuration manager
            
        Returns:
            Configured console handler
        """
        handler = logging.StreamHandler(sys.stdout)
        formatter = cls._create_formatter(config)
        handler.setFormatter(formatter)
        return handler
    
    @classmethod
    def _create_file_handler(cls, config: ConfigManager) -> logging.handlers.RotatingFileHandler:
        """Create rotating file handler
        
        Args:
            config: Configuration manager
            
        Returns:
            Configured file handler
        """
        log_file = config.get("logging.file.path", "logs/pipeline.log")
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        max_bytes = config.get("logging.file.max_bytes", 10485760)  # 10MB default
        backup_count = config.get("logging.file.backup_count", 5)
        
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        
        formatter = cls._create_formatter(config)
        handler.setFormatter(formatter)
        return handler
    
    @classmethod
    def _create_formatter(cls, config: ConfigManager) -> logging.Formatter:
        """Create log formatter
        
        Args:
            config: Configuration manager
            
        Returns:
            Log formatter
        """
        format_string = config.get(
            "logging.format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        return logging.Formatter(format_string)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get existing logger or create basic one
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]
        return logging.getLogger(name)


class ErrorTracker:
    """Track and report errors during pipeline execution"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize error tracker
        
        Args:
            logger: Logger instance for error reporting
        """
        self.logger = logger or logging.getLogger(__name__)
        self.errors = []
        self.warnings = []
        self.quarantine_path = Path("data/quarantine")
        self.quarantine_path.mkdir(parents=True, exist_ok=True)
    
    def log_error(self, error: Exception, context: str, record: Optional[dict] = None) -> None:
        """Log an error with context
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
            record: Optional data record that caused the error
        """
        error_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "record": record
        }
        
        self.errors.append(error_info)
        self.logger.error(
            f"{context}: {type(error).__name__} - {error}",
            extra={"record": record},
            exc_info=True
        )
    
    def log_warning(self, message: str, context: str) -> None:
        """Log a warning
        
        Args:
            message: Warning message
            context: Context where warning occurred
        """
        warning_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "message": message
        }
        
        self.warnings.append(warning_info)
        self.logger.warning(f"{context}: {message}")
    
    def quarantine_record(self, record: dict, reason: str) -> None:
        """Move failed record to quarantine
        
        Args:
            record: Data record that failed
            reason: Reason for quarantine
        """
        import json
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        source = record.get("_source", "unknown")
        filename = f"{source}_{timestamp}_{len(self.errors)}.json"
        
        quarantine_file = self.quarantine_path / filename
        
        quarantine_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "record": record
        }
        
        with open(quarantine_file, 'w') as f:
            json.dump(quarantine_data, f, indent=2)
        
        self.logger.info(f"Record quarantined: {filename}")
    
    def get_error_summary(self) -> dict:
        """Get summary of errors and warnings
        
        Returns:
            Dictionary with error statistics
        """
        error_types = {}
        for error in self.errors:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "error_types": error_types,
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    def clear(self) -> None:
        """Clear all tracked errors and warnings"""
        self.errors.clear()
        self.warnings.clear()


def setup_pipeline_logger(config: ConfigManager) -> logging.Logger:
    """Convenience function to setup pipeline logger
    
    Args:
        config: Configuration manager instance
        
    Returns:
        Configured logger
    """
    return LoggerSetup.setup_logging(config, "pipeline")
