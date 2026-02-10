# Docker Deployment Guide

## Building the Image

### Build locally
```bash
docker build -t data-pipeline:latest .
```

### Build with specific tag
```bash
docker build -t data-pipeline:v1.0.0 .
```

## Running the Container

### Using Docker Compose (Recommended for Development)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f pipeline

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up --build -d
```

### Using Docker Run
```bash
# Run container
docker run -d \
  --name data-pipeline \
  -e ENVIRONMENT=prod \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  data-pipeline:latest

# Run with custom command
docker run --rm \
  -v $(pwd)/data:/app/data \
  data-pipeline:latest \
  python -m pytest tests/
```

## Environment Variables

Set these in `.env` file or pass via `-e`:

- `ENVIRONMENT`: Environment name (dev, staging, prod)
- `DB_PASSWORD`: Database password
- `DB_USERNAME`: Database username
- `API_KEY`: API key for external services

## Health Checks

The container includes a health check that runs every 30 seconds:

```bash
# Check container health
docker ps
# Look for "healthy" status

# Inspect health check details
docker inspect --format='{{json .State.Health}}' data-pipeline
```

## Volume Mounts

### Data Directory
```bash
-v $(pwd)/data:/app/data
```
Persists ingested data and quarantine records.

### Logs Directory
```bash
-v $(pwd)/logs:/app/logs
```
Persists application logs.

### Configuration (Dev Only)
```bash
-v $(pwd)/config:/app/config:ro
```
Mount config as read-only for easy updates during development.

## Multi-Stage Build Benefits

1. **Smaller Image Size**: Runtime image doesn't include build tools
2. **Security**: Fewer packages means smaller attack surface
3. **Performance**: Faster image pulls and container starts

## Security Features

- **Non-root User**: Container runs as `pipeline` user
- **Minimal Base Image**: Uses slim Python image
- **Read-only Configs**: Configuration mounted as read-only
- **No Secrets in Image**: Sensitive data via environment variables

## Troubleshooting

### View container logs
```bash
docker logs data-pipeline
```

### Access container shell
```bash
docker exec -it data-pipeline /bin/bash
```

### Check running processes
```bash
docker exec data-pipeline ps aux
```

### Verify Python environment
```bash
docker exec data-pipeline python --version
docker exec data-pipeline pip list
```

## Production Deployment

For production, consider:

1. Use specific version tags (not `latest`)
2. Implement proper secrets management
3. Configure resource limits
4. Set up log aggregation
5. Use orchestration (Kubernetes, ECS, etc.)

### Example with Resource Limits
```bash
docker run -d \
  --name data-pipeline \
  --memory="512m" \
  --cpus="1.0" \
  -e ENVIRONMENT=prod \
  data-pipeline:v1.0.0
```

## CI/CD Integration

The Dockerfile is optimized for CI/CD:

- Layer caching for faster builds
- Multi-stage build reduces image size
- Health checks for availability monitoring
- Non-root user for security compliance
