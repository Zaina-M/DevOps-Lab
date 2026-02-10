# Data Ingestion & Validation Pipeline

## Vision & Scope

### Product Vision

This pipeline automates the ingestion, validation, and monitoring of data from multiple sources, ensuring data quality and reliability through continuous integration and automated testing. It provides a production-ready framework for detecting data anomalies early and maintaining data integrity across the ingestion lifecycle.

### Problem Statement

Modern data-driven systems require reliable data ingestion processes, but manual validation is error-prone, time-consuming, and fails to catch issues before they propagate downstream. Organizations struggle with inconsistent data quality, delayed error detection, and lack of visibility into data pipeline health, leading to poor decision-making and increased operational costs.

### Scope

#### In Scope

- Ingestion of data from multiple sources (CSV files, APIs, databases)
- Schema validation and data quality checks
- Automated unit and integration testing
- CI/CD pipeline with automated build, test, and deployment stages
- Monitoring and alerting for pipeline health and data quality metrics
- Error logging and basic reporting
- Docker containerization for consistent deployment
- Configuration management for different environments

#### Out of Scope

- Real-time streaming data processing
- Advanced machine learning-based anomaly detection
- Data transformation and complex ETL operations
- Multi-cloud deployment and orchestration
- Production-grade security features (encryption at rest, advanced authentication)
- Horizontal scaling and load balancing
- Data governance and compliance frameworks (GDPR, HIPAA)
- Advanced visualization dashboards

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Zaina-M/DevOps-Lab.git
cd "Agile and DevOps"
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Basic Usage

#### 1. Configuration Management

```python
from src.config_manager import ConfigManager

# Load configuration for development environment
config = ConfigManager(environment="dev")

# Access configuration values
batch_size = config.get("ingestion.batch_size")
log_level = config.get("logging.level")
```

#### 2. Ingest Data from CSV

```python
from src.ingestion import CSVDataSource, DataIngestionPipeline
from src.config_manager import ConfigManager

config = ConfigManager(environment="dev")

# Create CSV data source
csv_source = CSVDataSource(config, "data/sample_data.csv")

# Ingest data
records = list(csv_source.ingest())
print(f"Ingested {len(records)} records")
```

#### 3. Validate Data Against Schema

```python
from src.validation import SchemaValidator
from src.config_manager import ConfigManager

config = ConfigManager(environment="dev")

# Load schema
validator = SchemaValidator.from_file("schemas/user_schema.yaml", config)

# Validate a record
record = {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
}

result = validator.validate(record)
if result['valid']:
    print("Record is valid!")
else:
    print(f"Validation errors: {result['errors']}")
```

#### 4. Complete Pipeline Example

```python
from src.ingestion import CSVDataSource, DataIngestionPipeline
from src.validation import SchemaValidator, DataQualityChecker
from src.config_manager import ConfigManager

# Setup
config = ConfigManager(environment="dev")
pipeline = DataIngestionPipeline(config)

# Add data sources
csv_source = CSVDataSource(config, "data/sample_data.csv")
pipeline.add_source(csv_source)

# Run ingestion
records = pipeline.run()

# Validate records
validator = SchemaValidator.from_file("schemas/user_schema.yaml", config)
valid_records = []

for record in records:
    result = validator.validate(record)
    if result['valid']:
        valid_records.append(record)
    else:
        print(f"Invalid record: {result['errors']}")

# Check data quality
quality_checker = DataQualityChecker(config)
quality_report = quality_checker.check_quality(valid_records)
print(f"Quality Score: {quality_report['quality_score']}/100")
```

---

## Project Structure

```
.
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI/CD pipeline
├── config/
│   ├── default.yaml            # Default configuration
│   ├── dev.yaml                # Development environment config
│   └── prod.yaml               # Production environment config
├── data/
│   └── sample_data.csv         # Sample CSV data for testing
├── schemas/
│   └── user_schema.yaml        # User data schema definition
├── src/
│   ├── __init__.py
│   ├── config_manager.py       # Configuration management
│   ├── ingestion.py            # Data ingestion module
│   └── validation.py           # Schema validation module
├── tests/
│   ├── __init__.py
│   ├── test_config_manager.py  # Config tests
│   ├── test_ingestion.py       # Ingestion tests
│   └── test_validation.py      # Validation tests
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore patterns
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── SPRINT_0.md                 # Product backlog and planning
└── SPRINT_1.md                 # Sprint 1 execution report
```

---

## Features

### Completed (Sprint 1)

- **Multi-Source Data Ingestion**
  - CSV files with automatic metadata tracking
  - REST API with retry logic and authentication
  - Database support (PostgreSQL, MySQL)
  
- **Configuration Management**
  - Environment-specific configuration
  - YAML-based configuration files
  - Environment variable overrides for secrets
  
- **Schema Validation**
  - YAML schema definitions
  - Type, range, length, pattern validation
  - Email, phone, URL format validation
  - Data quality scoring and metrics
  
- **Testing & CI/CD**
  - 86% code coverage with 32 unit tests
  - Automated GitHub Actions pipeline
  - Coverage reporting and enforcement

### Planned (Future Sprints)

- Enhanced data quality checks
- Comprehensive error handling and logging
- Docker containerization
- Monitoring and alerting
- Real-time pipeline metrics

---

## Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_ingestion.py

# Run with verbose output
pytest -v

# Generate HTML coverage report
pytest --cov=src --cov-report=html
```

---

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration:

- **Triggers:** Push to main branch, pull requests
- **Stages:**
  1. Install dependencies
  2. Code linting with pylint
  3. Run tests with pytest
  4. Generate coverage reports
  5. Enforce 80% minimum coverage

View pipeline status in the [Actions tab](https://github.com/Zaina-M/DevOps-Lab/actions).

---

## Development

### Setting Up Development Environment

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install development dependencies:
```bash
pip install -r requirements.txt
```

3. Run tests before committing:
```bash
pytest
```

### Code Style

- Follow PEP 8 guidelines
- Use black for code formatting
- Run pylint for code quality checks

---

## Configuration

Configuration files are located in the `config/` directory:

- **default.yaml** - Base configuration for all environments
- **dev.yaml** - Development overrides (debug logging, smaller batches)
- **prod.yaml** - Production overrides (warning logging, larger batches)

Set the environment using the `ENVIRONMENT` variable:
```bash
export ENVIRONMENT=prod  # On Windows: set ENVIRONMENT=prod
```

---

## Contributing

1. Create a feature branch
2. Make your changes
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

## License

This project is part of an academic DevOps course and is for educational purposes.

---

## Project Status

**Current Sprint:** Sprint 1 (Completed)  
**Next Sprint:** Sprint 2  
**Overall Progress:** Foundation phase complete

See [SPRINT_1.md](SPRINT_1.md) for detailed Sprint 1 execution report.
