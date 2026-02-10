"""Schema Validation Module

Validates data against predefined schemas to ensure structural integrity.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml

from src.config_manager import ConfigManager


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class SchemaValidator:
    """Validates data records against defined schemas"""
    
    SUPPORTED_TYPES = {
        "string": str,
        "integer": int,
        "float": float,
        "boolean": bool,
        "date": str,  # ISO format strings
        "datetime": str,  # ISO format strings
        "email": str,
        "phone": str,
        "url": str
    }
    
    def __init__(self, schema: Dict[str, Any], config: ConfigManager):
        """Initialize schema validator
        
        Args:
            schema: Schema definition dictionary
            config: Configuration manager instance
        """
        self.schema = schema
        self.config = config
        self.strict_mode = config.get("validation.schema.strict_mode", True)
        self.allow_extra_fields = config.get("validation.schema.allow_extra_fields", False)
        
        self._validate_schema_definition()
    
    def _validate_schema_definition(self) -> None:
        """Validate that the schema definition itself is valid"""
        if "fields" not in self.schema:
            raise ValidationError("Schema must contain 'fields' definition")
        
        for field_name, field_def in self.schema["fields"].items():
            if "type" not in field_def:
                raise ValidationError(f"Field '{field_name}' missing 'type' definition")
            
            if field_def["type"] not in self.SUPPORTED_TYPES:
                raise ValidationError(
                    f"Field '{field_name}' has unsupported type: {field_def['type']}"
                )
    
    def validate(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single record against the schema
        
        Args:
            record: Data record to validate
            
        Returns:
            Validation result dictionary with 'valid' flag and 'errors' list
        """
        errors = []
        
        # Check for required fields
        required_fields = self._get_required_fields()
        missing_fields = required_fields - set(record.keys())
        
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check for extra fields (if strict mode)
        if not self.allow_extra_fields:
            extra_fields = set(record.keys()) - set(self.schema["fields"].keys()) - self._get_metadata_fields()
            if extra_fields:
                errors.append(f"Unexpected fields: {', '.join(extra_fields)}")
        
        # Validate each field
        for field_name, field_def in self.schema["fields"].items():
            if field_name in record:
                field_errors = self._validate_field(field_name, record[field_name], field_def)
                errors.extend(field_errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "record": record
        }
    
    def _get_required_fields(self) -> Set[str]:
        """Get set of required field names
        
        Returns:
            Set of required field names
        """
        return {
            name for name, field_def in self.schema["fields"].items()
            if field_def.get("required", False)
        }
    
    def _get_metadata_fields(self) -> Set[str]:
        """Get set of metadata field names (added by ingestion)
        
        Returns:
            Set of metadata field names
        """
        return {
            "_source", "_source_file", "_source_endpoint", "_source_db_type",
            "_ingestion_timestamp", "_row_number", "_record_number"
        }
    
    def _validate_field(
        self,
        field_name: str,
        value: Any,
        field_def: Dict[str, Any]
    ) -> List[str]:
        """Validate a single field value
        
        Args:
            field_name: Name of the field
            value: Field value
            field_def: Field definition from schema
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check for null values
        if value is None or value == "":
            if field_def.get("required", False):
                errors.append(f"Field '{field_name}' is required but got null/empty")
            return errors
        
        # Type validation
        expected_type = field_def["type"]
        if not self._validate_type(value, expected_type):
            errors.append(
                f"Field '{field_name}' has invalid type. "
                f"Expected {expected_type}, got {type(value).__name__}"
            )
            return errors
        
        # Range validation for numeric fields
        if expected_type in ["integer", "float"]:
            if "min" in field_def and value < field_def["min"]:
                errors.append(f"Field '{field_name}' value {value} below minimum {field_def['min']}")
            
            if "max" in field_def and value > field_def["max"]:
                errors.append(f"Field '{field_name}' value {value} above maximum {field_def['max']}")
        
        # Length validation for strings
        if expected_type == "string":
            if "min_length" in field_def and len(str(value)) < field_def["min_length"]:
                errors.append(f"Field '{field_name}' too short (min: {field_def['min_length']})")
            
            if "max_length" in field_def and len(str(value)) > field_def["max_length"]:
                errors.append(f"Field '{field_name}' too long (max: {field_def['max_length']})")
        
        # Pattern validation
        if "pattern" in field_def:
            if not re.match(field_def["pattern"], str(value)):
                errors.append(f"Field '{field_name}' does not match required pattern")
        
        # Enum validation
        if "enum" in field_def:
            if value not in field_def["enum"]:
                errors.append(
                    f"Field '{field_name}' value '{value}' not in allowed values: {field_def['enum']}"
                )
        
        return errors
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type
        
        Args:
            value: Value to check
            expected_type: Expected type name
            
        Returns:
            True if type matches, False otherwise
        """
        # Try to convert string to expected type
        if isinstance(value, str):
            try:
                if expected_type == "integer":
                    int(value)
                    return True
                elif expected_type == "float":
                    float(value)
                    return True
                elif expected_type == "boolean":
                    return value.lower() in ["true", "false", "1", "0"]
                elif expected_type == "email":
                    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", value))
                elif expected_type == "phone":
                    return bool(re.match(r"^\+?[\d\s\-\(\)]{10,}$", value))
                elif expected_type == "url":
                    return bool(re.match(r"^https?://", value))
                elif expected_type in ["date", "datetime"]:
                    # Basic ISO format check
                    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", value))
                else:  # string
                    return True
            except (ValueError, TypeError):
                return False
        
        # Direct type checking
        expected_python_type = self.SUPPORTED_TYPES.get(expected_type)
        return isinstance(value, expected_python_type)
    
    @classmethod
    def from_file(cls, schema_path: str, config: ConfigManager) -> "SchemaValidator":
        """Create validator from schema file
        
        Args:
            schema_path: Path to YAML schema file
            config: Configuration manager instance
            
        Returns:
            SchemaValidator instance
        """
        path = Path(schema_path)
        if not path.exists():
            raise ValidationError(f"Schema file not found: {schema_path}")
        
        with open(path, 'r') as f:
            schema = yaml.safe_load(f)
        
        return cls(schema, config)


class DataQualityChecker:
    """Performs data quality checks on ingested data"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
    
    def check_quality(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform quality checks on a batch of records
        
        Args:
            records: List of data records
            
        Returns:
            Quality report dictionary
        """
        if not records:
            return {
                "total_records": 0,
                "quality_score": 0,
                "checks": {}
            }
        
        checks = {}
        
        # Null check
        if self.config.get("validation.quality_checks.null_check", True):
            checks["null_percentage"] = self._check_null_values(records)
        
        # Duplicate check
        checks["duplicate_count"] = self._check_duplicates(records)
        
        # Calculate overall quality score
        null_threshold = self.config.get("validation.thresholds.max_null_percentage", 5)
        null_penalty = min(checks.get("null_percentage", 0) / null_threshold, 1.0)
        
        quality_score = max(0, 100 - (null_penalty * 50))
        
        return {
            "total_records": len(records),
            "quality_score": round(quality_score, 2),
            "checks": checks
        }
    
    def _check_null_values(self, records: List[Dict[str, Any]]) -> float:
        """Check percentage of null values across all fields
        
        Args:
            records: List of records
            
        Returns:
            Percentage of null values
        """
        if not records:
            return 0.0
        
        total_values = 0
        null_count = 0
        
        for record in records:
            for key, value in record.items():
                if not key.startswith("_"):  # Skip metadata fields
                    total_values += 1
                    if value is None or value == "":
                        null_count += 1
        
        return round((null_count / total_values * 100), 2) if total_values > 0 else 0.0
    
    def _check_duplicates(self, records: List[Dict[str, Any]]) -> int:
        """Check for duplicate records
        
        Args:
            records: List of records
            
        Returns:
            Count of duplicate records
        """
        seen = set()
        duplicates = 0
        
        for record in records:
            # Create hashable representation (exclude metadata)
            record_tuple = tuple(
                sorted(
                    (k, v) for k, v in record.items()
                    if not k.startswith("_")
                )
            )
            
            if record_tuple in seen:
                duplicates += 1
            else:
                seen.add(record_tuple)
        
        return duplicates
