FROM python:3.11-slim

WORKDIR /tests

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy test requirements
COPY tests/e2e/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy core library
COPY spreadpilot-core /spreadpilot-core
RUN pip install -e /spreadpilot-core

# Copy test files
COPY tests/e2e /tests/e2e

# Set environment
ENV PYTHONPATH=/tests:/spreadpilot-core
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["pytest", "/tests/e2e", "-v", "--tb=short"]