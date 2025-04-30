# Use Python 3.11 slim as base image
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (Paths relative to project root context '.')
COPY spreadpilot-core/setup.py spreadpilot-core/
COPY spreadpilot-core/pyproject.toml spreadpilot-core/
COPY spreadpilot-core/README.md spreadpilot-core/
COPY spreadpilot-core/spreadpilot_core spreadpilot-core/spreadpilot_core

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ./spreadpilot-core && \
    pip install --no-cache-dir fastapi uvicorn google-cloud-firestore google-cloud-secret-manager

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (Path relative to project root context '.')
COPY trading-bot/app /app/app

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]