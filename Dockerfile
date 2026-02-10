# Multi-stage build for Data Ingestion & Validation Pipeline

# Stage 1: Builder
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r pipeline && useradd -r -g pipeline pipeline

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/pipeline/.local

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY schemas/ ./schemas/

# Create necessary directories
RUN mkdir -p logs data/quarantine && \
    chown -R pipeline:pipeline /app

# Set Python path
ENV PYTHONPATH=/app
ENV PATH=/home/pipeline/.local/bin:$PATH

# Switch to non-root user
USER pipeline

# Health check endpoint (requires adding a simple health check script)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command (can be overridden)
CMD ["python", "-c", "print('Pipeline container ready. Run your ingestion script.')"]
