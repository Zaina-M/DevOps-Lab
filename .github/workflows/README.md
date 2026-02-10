# GitHub Actions CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment.

## Workflows

### CI/CD Pipeline (`ci.yml`)

Triggers on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

#### Jobs

**1. Test and Build**
- Runs on Ubuntu latest with Python 3.9, 3.10, and 3.11
- Installs dependencies
- Runs linting checks (pylint)
- Checks code formatting (black)
- Executes unit tests with coverage reporting
- Uploads coverage to Codecov
- Enforces 80% minimum test coverage

**2. Security Scan**
- Checks for known vulnerabilities in dependencies (safety)
- Scans code for security issues (bandit)

**3. Build Status Summary**
- Aggregates results from all jobs
- Provides overall pipeline status

## Local Testing

Run the same checks locally before pushing:

```bash
# Install dependencies
pip install -r requirements.txt

# Run linting
pylint src/

# Check formatting
black --check src/ tests/

# Run tests
pytest tests/ --cov=src --cov-report=term-missing

# Security scans
safety check
bandit -r src/
```

## Coverage Reporting

Test coverage reports are generated in:
- Terminal output (during test run)
- `htmlcov/` directory (open `index.html` in browser)
- `coverage.xml` (for CI tools)

## Pipeline Status

The pipeline status badge can be displayed in the README:

```markdown
![CI/CD Pipeline](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/ci.yml/badge.svg)
```
