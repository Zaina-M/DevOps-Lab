# Data Ingestion & Validation Pipeline

> **A course prototype data pipeline with automated ingestion, validation, monitoring, and quality checks for multi-source data.**

[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue)](https://github.com/Zaina-M/DevOps-Lab/actions)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen)](#docker)
[![Coverage](https://img.shields.io/badge/coverage-90.48%25-brightgreen)](#running-tests)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

## Overview

A scalable data pipeline that ingests from **CSV, APIs, and databases**, validates against custom schemas, monitors data quality in real-time, and provides comprehensive logging and alerting. Built with DevOps best practices including automated testing, CI/CD, and Docker containerization.

## Key Features

### ðŸš€ Data Ingestion
- **Multi-source support**: CSV files, REST APIs, PostgreSQL, MySQL
- **Memory-efficient**: Iterator-based processing for large datasets
- **Resilient**: Automatic retry logic with exponential backoff
- **Metadata tracking**: Timestamps and source information on every record

### âœ… Validation & Quality
- **Schema validation**: 9 data types (string, integer, email, phone, URL, etc.)
- **Quality scoring**: Automated quality metrics and thresholds
- **Flexible rules**: Required fields, ranges, patterns, enums

### ðŸ“Š Monitoring & Observability
- **Real-time metrics**: Ingestion rates, validation success, quality scores
- **Health checks**: Configurable thresholds and automated alerts
- **Structured logging**: Rotating logs with error tracking and quarantine system

### ðŸ³ DevOps Ready
- **Docker**: Multi-stage builds with PostgreSQL integration
- **CI/CD**: Automated testing and linting via GitHub Actions
- **Environment configs**: Separate dev/prod configurations
- **64 unit tests** with pytest and coverage reporting

---

## Quick Start

ðŸ“– **[Complete User Guide](USER_GUIDE.md)** | ðŸ³ **[Docker Guide](docs/DOCKER.md)** | ðŸ’¡ **[Examples](examples/)**

```bash
# Clone and setup
git clone https://github.com/Zaina-M/DevOps-Lab.git
cd "Agile and DevOps"
pip install -r requirements.txt
cp .env.example .env

# Run example pipeline with Docker
docker-compose up -d
docker-compose exec pipeline python examples/run_pipeline.py

# Or run tests locally
pytest --cov=src
```

## Usage Example

```python
from src.config_manager import ConfigManager
from src.ingestion import CSVDataSource, DataIngestionPipeline
from src.validation import SchemaValidator, DataQualityChecker
from src.monitoring import PipelineMonitor

# Initialize
config = ConfigManager(environment="dev")
monitor = PipelineMonitor(config)

# Ingest from CSV
pipeline = DataIngestionPipeline(config)
pipeline.add_source(CSVDataSource(config, "data/sample_data.csv"))
records = pipeline.run()

# Validate
validator = SchemaValidator.from_file("schemas/user_schema.yaml", config)
valid_records = [r for r in records if validator.validate(r)['valid']]

# Check quality and monitor
quality_checker = DataQualityChecker(config)
quality_report = quality_checker.check_quality(valid_records)
print(f"Quality Score: {quality_report['quality_score']}/100")
print(f"Pipeline Health: {monitor.check_health()}")
```

**See [USER_GUIDE.md](USER_GUIDE.md) for complete examples including API and database ingestion.**

---

## Project Structure

```
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
├── README.md                   # Project documentation
├── SPRINT_0.md                 # Product backlog and planning
└── SPRINT_1.md                 # Sprint 1 execution report
```
---

## Architecture
```
┌──────────────────┐
│   Data Sources   │  ← CSV, API, Database
└─────────┬────────┘
          ↓
┌──────────────────┐
│    Ingestion     │  ← Batch processing, retry logic
└─────────┬────────┘
          ↓
┌──────────────────┐
│    Validation    │  ← Schema checks, quality scoring
└─────────┬────────┘
          ↓
┌──────────────────┐
│   Monitoring     │  ← Metrics, health checks, alerts
└─────────┬────────┘
          ↓
┌──────────────────┐
│  Output / Logs   │  ← Valid data, error quarantine
└──────────────────┘
```

---

## Testing & CI/CD

**64 unit tests** covering configuration, ingestion, validation, logging, and monitoring.

```bash
pytest --cov=src                    # Run all tests with coverage
pytest tests/test_ingestion.py -v  # Run specific module
```

**GitHub Actions CI/CD:**
- âœ… Automated linting (pylint, black)
- âœ… Test suite execution on every push
- âœ… Coverage reporting (80% threshold)
- âœ… Multi-environment validation

[View pipeline status â†’](https://github.com/Zaina-M/DevOps-Lab/actions)

---

## Docker Deployment

```bash
# Start pipeline + PostgreSQL
docker-compose up

# Build custom image
docker build -t data-pipeline .

# Run with custom config
docker run -v $(pwd)/config:/app/config data-pipeline
```

See [docs/DOCKER.md](docs/DOCKER.md) for complete deployment guide.

---

## Configuration

Environment-specific YAML configs in `config/`:

| File | Purpose | Key Settings |
|------|---------|-------------|
| `default.yaml` | Base config | batch_size: 1000, workers: 4 |
| `dev.yaml` | Development | DEBUG logs, batch_size: 100 |
| `prod.yaml` | Production | WARNING logs, batch_size: 5000 |

```bash
# Switch environments
export ENVIRONMENT=prod  # Windows: set ENVIRONMENT=prod
```

---

## Project Status

| Sprint | Focus | Points | Status |
|--------|-------|-----------|--------|
| Sprint 1 | Foundation (ingestion, validation, config) | 16/16 | âœ… Complete |
| Sprint 2 | Observability (logging, monitoring, Docker) | 23/23 | âœ… Complete |
| Sprint 3 | Integration tests, CI/CD, security | 24 | ðŸ“… Planned |

**Progress:** 39/55 story points (71%)  
**Test Coverage:** 90.48% (latest `coverage.xml`)

---

## Documentation

| Resource | Description |
|----------|-------------|
| **[USER_GUIDE.md](USER_GUIDE.md)** | Complete setup and usage instructions |
| **[DOCKER.md](docs/DOCKER.md)** | Container deployment guide |
| **[SPRINT_0.md](SPRINT_0.md)** | Product backlog and planning |
| **[SPRINT_1.md](SPRINT_1.md)** | Sprint 1 execution report |
| **[SPRINT_2.md](SPRINT_2.md)** | Sprint 2 execution report |

---

## License

Academic project for DevOps coursework

