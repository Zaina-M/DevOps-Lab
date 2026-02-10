"""Unit tests for Data Ingestion Module"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.ingestion import (
    CSVDataSource,
    APIDataSource,
    DatabaseDataSource,
    DataIngestionPipeline,
    IngestionError
)
from src.config_manager import ConfigManager


@pytest.fixture
def config():
    """Fixture providing configuration manager"""
    return ConfigManager(config_dir="config", environment="dev")


@pytest.fixture
def sample_csv_file():
    """Fixture creating a temporary CSV file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("id,name,email\n")
        f.write("1,John Doe,john@example.com\n")
        f.write("2,Jane Smith,jane@example.com\n")
        f.write("3,Bob Johnson,bob@example.com\n")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestCSVDataSource:
    """Test suite for CSV data source"""
    
    def test_csv_ingestion_success(self, config, sample_csv_file):
        """Test successful CSV ingestion"""
        source = CSVDataSource(config, sample_csv_file)
        
        records = list(source.ingest())
        
        assert len(records) == 3
        assert records[0]['name'] == 'John Doe'
        assert records[1]['email'] == 'jane@example.com'
        
        # Check metadata fields
        assert '_source' in records[0]
        assert records[0]['_source'] == 'csv'
        assert '_ingestion_timestamp' in records[0]
    
    def test_csv_file_not_found(self, config):
        """Test error handling for missing CSV file"""
        with pytest.raises(IngestionError, match="CSV file not found"):
            CSVDataSource(config, "nonexistent_file.csv")
    
    def test_csv_stats(self, config, sample_csv_file):
        """Test ingestion statistics"""
        source = CSVDataSource(config, sample_csv_file)
        list(source.ingest())  # Consume iterator
        
        stats = source.get_stats()
        assert stats['success'] == 3
        assert stats['errors'] == 0


class TestAPIDataSource:
    """Test suite for API data source"""
    
    @patch('src.ingestion.requests.get')
    def test_api_ingestion_success(self, mock_get, config):
        """Test successful API ingestion"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        source = APIDataSource(config, "https://api.example.com/data")
        records = list(source.ingest())
        
        assert len(records) == 2
        assert records[0]['name'] == 'Item 1'
        assert '_source' in records[0]
        assert records[0]['_source'] == 'api'
    
    @patch('src.ingestion.requests.get')
    def test_api_retry_logic(self, mock_get, config):
        """Test API retry mechanism on failure"""
        # First two calls fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = Exception("Connection error")
        
        mock_response_success = Mock()
        mock_response_success.json.return_value = [{"id": 1}]
        mock_response_success.raise_for_status = Mock()
        
        mock_get.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ]
        
        source = APIDataSource(config, "https://api.example.com/data")
        
        # Should succeed after retries
        records = list(source.ingest())
        assert len(records) == 1
        assert mock_get.call_count == 3
    
    @patch('src.ingestion.requests.get')
    def test_api_auth_header(self, mock_get, config, monkeypatch):
        """Test API authentication header"""
        monkeypatch.setenv("API_KEY", "test_key_123")
        config.reload()
        
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        source = APIDataSource(config, "https://api.example.com/data")
        list(source.ingest())
        
        # Check that auth header was included
        call_args = mock_get.call_args
        headers = call_args.kwargs['headers']
        assert 'Authorization' in headers


class TestDatabaseDataSource:
    """Test suite for Database data source"""
    
    @patch('src.ingestion.psycopg2.connect')
    def test_postgres_ingestion(self, mock_connect, config):
        """Test PostgreSQL ingestion"""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchmany.side_effect = [
            [(1, 'Item 1'), (2, 'Item 2')],
            []  # No more rows
        ]
        
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        source = DatabaseDataSource(config, "SELECT * FROM users", db_type="postgresql")
        records = list(source.ingest())
        
        assert len(records) == 2
        assert records[0]['id'] == 1
        assert records[0]['name'] == 'Item 1'
        assert '_source' in records[0]
        assert records[0]['_source'] == 'database'
    
    def test_unsupported_database_type(self, config):
        """Test error for unsupported database type"""
        with pytest.raises(IngestionError, match="Unsupported database type"):
            DatabaseDataSource(config, "SELECT * FROM users", db_type="oracle")


class TestDataIngestionPipeline:
    """Test suite for Data Ingestion Pipeline"""
    
    def test_pipeline_multiple_sources(self, config, sample_csv_file):
        """Test pipeline with multiple data sources"""
        pipeline = DataIngestionPipeline(config)
        
        # Add CSV source
        csv_source = CSVDataSource(config, sample_csv_file)
        pipeline.add_source(csv_source)
        
        records = pipeline.run()
        
        assert len(records) >= 3  # At least CSV records
    
    def test_pipeline_continues_on_source_failure(self, config, sample_csv_file):
        """Test that pipeline continues when one source fails"""
        pipeline = DataIngestionPipeline(config)
        
        # Add a failing source
        failing_source = CSVDataSource(config, sample_csv_file)
        failing_source.ingest = Mock(side_effect=IngestionError("Test error"))
        pipeline.add_source(failing_source)
        
        # Add a successful source
        success_source = CSVDataSource(config, sample_csv_file)
        pipeline.add_source(success_source)
        
        # Should not raise exception, should continue to successful source
        records = pipeline.run()
        
        # Should have records from successful source
        assert len(records) >= 3
