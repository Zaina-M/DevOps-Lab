"""Data Ingestion Module

Handles data ingestion from multiple sources including CSV files,
REST APIs, and databases.
"""

import csv
import logging
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator
from datetime import datetime

import requests
import pandas as pd
import psycopg2
import pymysql

from src.config_manager import ConfigManager


logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Raised when data ingestion fails"""
    pass


class DataSource(ABC):
    """Abstract base class for data sources"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.error_count = 0
        self.success_count = 0
    
    @abstractmethod
    def ingest(self) -> Iterator[Dict[str, Any]]:
        """Ingest data from the source
        
        Yields:
            Dictionary representing a single record
        """
        pass
    
    def get_stats(self) -> Dict[str, int]:
        """Get ingestion statistics
        
        Returns:
            Dictionary with success and error counts
        """
        return {
            "success": self.success_count,
            "errors": self.error_count
        }


class CSVDataSource(DataSource):
    """Ingest data from CSV files"""
    
    def __init__(self, config: ConfigManager, file_path: str):
        super().__init__(config)
        self.file_path = Path(file_path)
        
        if not self.file_path.exists():
            raise IngestionError(f"CSV file not found: {file_path}")
        
        # Check file size
        file_size_mb = self.file_path.stat().st_size / (1024 * 1024)
        max_size = config.get("ingestion.sources.csv.max_file_size_mb", 100)
        
        if file_size_mb > max_size:
            raise IngestionError(
                f"CSV file too large: {file_size_mb:.2f}MB > {max_size}MB"
            )
    
    def ingest(self) -> Iterator[Dict[str, Any]]:
        """Ingest data from CSV file
        
        Yields:
            Dictionary representing a single row
        """
        delimiter = self.config.get("ingestion.sources.csv.delimiter", ",")
        encoding = self.config.get("ingestion.sources.csv.encoding", "utf-8")
        
        logger.info(f"Starting CSV ingestion from: {self.file_path}")
        
        try:
            with open(self.file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                    try:
                        # Add metadata
                        row['_source'] = 'csv'
                        row['_source_file'] = str(self.file_path)
                        row['_ingestion_timestamp'] = datetime.utcnow().isoformat()
                        row['_row_number'] = row_num
                        
                        self.success_count += 1
                        yield row
                        
                    except Exception as e:
                        self.error_count += 1
                        logger.error(f"Error processing row {row_num}: {e}")
                        continue
        
        except Exception as e:
            raise IngestionError(f"Failed to read CSV file: {e}")
        
        logger.info(f"CSV ingestion complete. Success: {self.success_count}, Errors: {self.error_count}")


class APIDataSource(DataSource):
    """Ingest data from REST APIs"""
    
    def __init__(self, config: ConfigManager, endpoint: str, params: Optional[Dict] = None):
        super().__init__(config)
        self.endpoint = endpoint
        self.params = params or {}
        self.timeout = config.get("ingestion.sources.api.timeout_seconds", 30)
        self.max_retries = config.get("ingestion.sources.api.max_retries", 3)
        self.retry_delay = config.get("ingestion.sources.api.retry_delay_seconds", 5)
    
    def _make_request_with_retry(self) -> requests.Response:
        """Make HTTP request with retry logic
        
        Returns:
            Response object
            
        Raises:
            IngestionError if all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.endpoint,
                    params=self.params,
                    timeout=self.timeout,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"API request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise IngestionError(f"API request failed after {self.max_retries} attempts: {e}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers including authentication
        
        Returns:
            Dictionary of headers
        """
        headers = {"Accept": "application/json"}
        
        api_key = self.config.get("api.api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        return headers
    
    def ingest(self) -> Iterator[Dict[str, Any]]:
        """Ingest data from API endpoint
        
        Yields:
            Dictionary representing a single record
        """
        logger.info(f"Starting API ingestion from: {self.endpoint}")
        
        try:
            response = self._make_request_with_retry()
            data = response.json()
            
            # Handle different response formats
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict) and 'data' in data:
                records = data['data']
            elif isinstance(data, dict) and 'results' in data:
                records = data['results']
            else:
                records = [data]
            
            for idx, record in enumerate(records):
                try:
                    # Add metadata
                    record['_source'] = 'api'
                    record['_source_endpoint'] = self.endpoint
                    record['_ingestion_timestamp'] = datetime.utcnow().isoformat()
                    record['_record_number'] = idx + 1
                    
                    self.success_count += 1
                    yield record
                    
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error processing API record {idx}: {e}")
                    continue
        
        except Exception as e:
            raise IngestionError(f"API ingestion failed: {e}")
        
        logger.info(f"API ingestion complete. Success: {self.success_count}, Errors: {self.error_count}")


class DatabaseDataSource(DataSource):
    """Ingest data from databases (PostgreSQL, MySQL)"""
    
    def __init__(
        self,
        config: ConfigManager,
        query: str,
        db_type: str = "postgresql"
    ):
        super().__init__(config)
        self.query = query
        self.db_type = db_type.lower()
        
        if self.db_type not in ["postgresql", "mysql"]:
            raise IngestionError(f"Unsupported database type: {db_type}")
    
    def _get_connection(self):
        """Get database connection based on type
        
        Returns:
            Database connection object
        """
        host = self.config.get("database.host", "localhost")
        port = self.config.get("database.port", 5432)
        database = self.config.get("database.database")
        username = self.config.get("database.username")
        password = self.config.get("database.password")
        timeout = self.config.get("ingestion.sources.database.connection_timeout", 10)
        
        try:
            if self.db_type == "postgresql":
                return psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=timeout
                )
            else:  # mysql
                return pymysql.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    connect_timeout=timeout
                )
        except Exception as e:
            raise IngestionError(f"Database connection failed: {e}")
    
    def ingest(self) -> Iterator[Dict[str, Any]]:
        """Ingest data from database query
        
        Yields:
            Dictionary representing a single row
        """
        logger.info(f"Starting database ingestion ({self.db_type})")
        
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Execute query
            cursor.execute(self.query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch and yield rows
            batch_size = self.config.get("ingestion.batch_size", 1000)
            
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                
                for row in rows:
                    try:
                        # Convert row to dictionary
                        record = dict(zip(columns, row))
                        
                        # Add metadata
                        record['_source'] = 'database'
                        record['_source_db_type'] = self.db_type
                        record['_ingestion_timestamp'] = datetime.utcnow().isoformat()
                        
                        self.success_count += 1
                        yield record
                        
                    except Exception as e:
                        self.error_count += 1
                        logger.error(f"Error processing database row: {e}")
                        continue
        
        except Exception as e:
            raise IngestionError(f"Database ingestion failed: {e}")
        
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        
        logger.info(f"Database ingestion complete. Success: {self.success_count}, Errors: {self.error_count}")


class DataIngestionPipeline:
    """Main pipeline for orchestrating data ingestion"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.sources: List[DataSource] = []
    
    def add_source(self, source: DataSource) -> None:
        """Add a data source to the pipeline
        
        Args:
            source: DataSource instance
        """
        self.sources.append(source)
    
    def run(self) -> List[Dict[str, Any]]:
        """Run the ingestion pipeline
        
        Returns:
            List of all ingested records
        """
        all_records = []
        
        logger.info(f"Starting ingestion pipeline with {len(self.sources)} sources")
        
        for idx, source in enumerate(self.sources, start=1):
            logger.info(f"Processing source {idx}/{len(self.sources)}: {source.__class__.__name__}")
            
            try:
                for record in source.ingest():
                    all_records.append(record)
                
                stats = source.get_stats()
                logger.info(f"Source {idx} complete: {stats}")
                
            except IngestionError as e:
                logger.error(f"Source {idx} failed: {e}")
                continue
        
        logger.info(f"Pipeline complete. Total records ingested: {len(all_records)}")
        return all_records
