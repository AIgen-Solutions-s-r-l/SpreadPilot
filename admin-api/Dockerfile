FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY admin-api/requirements.in .
RUN pip install --no-cache-dir pip-tools && \
    pip-compile requirements.in && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY admin-api/ .
COPY spreadpilot-core/ /app/spreadpilot-core/

# Install the core library in development mode
RUN pip install -e /app/spreadpilot-core

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Expose the port
EXPOSE 8080 8002

# Default to running main.py, but allow override via ADMIN_API_MODULE env var
ENV ADMIN_API_MODULE=main:app

# Run the application
CMD ["sh", "-c", "uvicorn ${ADMIN_API_MODULE} --host 0.0.0.0 --port ${ADMIN_API_PORT:-8080}"]