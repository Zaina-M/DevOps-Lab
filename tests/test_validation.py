"""Unit tests for Schema Validation Module"""

import pytest
import tempfile
from pathlib import Path

from src.validation import SchemaValidator, DataQualityChecker, ValidationError
from src.config_manager import ConfigManager


@pytest.fixture
def config():
    """Fixture providing configuration manager"""
    return ConfigManager(config_dir="config", environment="dev")


@pytest.fixture
def sample_schema():
    """Fixture providing a sample schema"""
    return {
        "name": "test_schema",
        "fields": {
            "id": {
                "type": "integer",
                "required": True,
                "min": 1
            },
            "name": {
                "type": "string",
                "required": True,
                "min_length": 2,
                "max_length": 50
            },
            "email": {
                "type": "email",
                "required": True
            },
            "age": {
                "type": "integer",
                "required": False,
                "min": 0,
                "max": 150
            }
        }
    }


class TestSchemaValidator:
    """Test suite for SchemaValidator"""
    
    def test_valid_record(self, config, sample_schema):
        """Test validation of a valid record"""
        validator = SchemaValidator(sample_schema, config)
        
        record = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
        
        result = validator.validate(record)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_missing_required_field(self, config, sample_schema):
        """Test validation fails for missing required field"""
        validator = SchemaValidator(sample_schema, config)
        
        record = {
            "id": 1,
            "name": "John Doe"
            # Missing required email field
        }
        
        result = validator.validate(record)
        
        assert result['valid'] is False
        assert any("email" in error.lower() for error in result['errors'])
    
    def test_invalid_type(self, config, sample_schema):
        """Test validation fails for invalid type"""
        validator = SchemaValidator(sample_schema, config)
        
        record = {
            "id": "not_a_number",  # Should be integer
            "name": "John Doe",
            "email": "john@example.com"
        }
        
        result = validator.validate(record)
        
        assert result['valid'] is False
        assert any("type" in error.lower() for error in result['errors'])
    
    def test_invalid_email(self, config, sample_schema):
        """Test validation fails for invalid email format"""
        validator = SchemaValidator(sample_schema, config)
        
        record = {
            "id": 1,
            "name": "John Doe",
            "email": "invalid_email"  # Invalid email format
        }
        
        result = validator.validate(record)
        
        assert result['valid'] is False
    
    def test_range_validation(self, config, sample_schema):
        """Test range validation for numeric fields"""
        validator = SchemaValidator(sample_schema, config)
        
        # Age too high
        record = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "age": 200  # Above max of 150
        }
        
        result = validator.validate(record)
        
        assert result['valid'] is False
        assert any("age" in error.lower() and "maximum" in error.lower() for error in result['errors'])
    
    def test_string_length_validation(self, config):
        """Test string length validation"""
        schema = {
            "name": "test",
            "fields": {
                "username": {
                    "type": "string",
                    "required": True,
                    "min_length": 3,
                    "max_length": 10
                }
            }
        }
        
        validator = SchemaValidator(schema, config)
        
        # Too short
        result = validator.validate({"username": "ab"})
        assert result['valid'] is False
        
        # Too long
        result = validator.validate({"username": "verylongusername"})
        assert result['valid'] is False
        
        # Just right
        result = validator.validate({"username": "john"})
        assert result['valid'] is True
    
    def test_enum_validation(self, config):
        """Test enum validation"""
        schema = {
            "name": "test",
            "fields": {
                "status": {
                    "type": "string",
                    "required": True,
                    "enum": ["active", "inactive", "pending"]
                }
            }
        }
        
        validator = SchemaValidator(schema, config)
        
        # Valid enum value
        result = validator.validate({"status": "active"})
        assert result['valid'] is True
        
        # Invalid enum value
        result = validator.validate({"status": "unknown"})
        assert result['valid'] is False
    
    def test_allow_extra_fields(self, config, sample_schema):
        """Test allowing extra fields not in schema"""
        # Create config that allows extra fields
        config_dict = config.get_all()
        config_dict['validation']['schema']['allow_extra_fields'] = True
        
        validator = SchemaValidator(sample_schema, config)
        validator.allow_extra_fields = True
        
        record = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "extra_field": "extra_value"
        }
        
        result = validator.validate(record)
        assert result['valid'] is True
    
    def test_load_schema_from_file(self, config):
        """Test loading schema from YAML file"""
        validator = SchemaValidator.from_file("schemas/user_schema.yaml", config)
        
        record = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "city": "New York",
            "country": "USA"
        }
        
        result = validator.validate(record)
        assert result['valid'] is True
    
    def test_invalid_schema_definition(self, config):
        """Test error handling for invalid schema definition"""
        invalid_schema = {
            "name": "test",
            # Missing 'fields' key
        }
        
        with pytest.raises(ValidationError, match="must contain 'fields'"):
            SchemaValidator(invalid_schema, config)


class TestDataQualityChecker:
    """Test suite for DataQualityChecker"""
    
    def test_null_value_check(self, config):
        """Test null value percentage calculation"""
        checker = DataQualityChecker(config)
        
        records = [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "", "email": "jane@example.com"},  # Empty name
            {"id": 3, "name": "Bob", "email": None},  # Null email
        ]
        
        report = checker.check_quality(records)
        
        assert "null_percentage" in report['checks']
        assert report['checks']['null_percentage'] > 0
    
    def test_duplicate_check(self, config):
        """Test duplicate record detection"""
        checker = DataQualityChecker(config)
        
        records = [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "Jane"},
            {"id": 1, "name": "John"},  # Duplicate
        ]
        
        report = checker.check_quality(records)
        
        assert "duplicate_count" in report['checks']
        assert report['checks']['duplicate_count'] == 1
    
    def test_quality_score_calculation(self, config):
        """Test overall quality score calculation"""
        checker = DataQualityChecker(config)
        
        # Perfect data
        good_records = [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "Jane", "email": "jane@example.com"},
        ]
        
        report = checker.check_quality(good_records)
        
        assert report['quality_score'] > 90
        assert report['total_records'] == 2
    
    def test_empty_records(self, config):
        """Test quality check on empty record list"""
        checker = DataQualityChecker(config)
        
        report = checker.check_quality([])
        
        assert report['total_records'] == 0
        assert report['quality_score'] == 0
