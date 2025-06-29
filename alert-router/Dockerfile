FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY alert-router/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared core library
COPY spreadpilot-core /app/spreadpilot-core
RUN pip install -e /app/spreadpilot-core

# Copy application code
COPY alert-router/app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8006/health'); r.raise_for_status()"

# Run the application
CMD ["uvicorn", "app.alert_router:app", "--host", "0.0.0.0", "--port", "8006"]