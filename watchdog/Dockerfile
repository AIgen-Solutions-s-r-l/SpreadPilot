# Use Python 3.11 slim as base image
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies and pip-tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && pip install --no-cache-dir --upgrade pip pip-tools && \
    apt-get purge -y --auto-remove build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy core library source
# Ensure these paths are relative to the build context root (where docker build is run)
COPY spreadpilot-core/setup.py spreadpilot-core/
COPY spreadpilot-core/pyproject.toml spreadpilot-core/
COPY spreadpilot-core/README.md spreadpilot-core/
COPY spreadpilot-core/spreadpilot_core spreadpilot-core/spreadpilot_core

# Copy watchdog requirements
COPY watchdog/requirements.in ./watchdog/

# Compile requirements and install dependencies including the core library
# This installs core in editable mode first, then installs compiled requirements
RUN pip install --no-cache-dir -e ./spreadpilot-core && \
    pip-compile --strip-extras watchdog/requirements.in -o watchdog/requirements.txt && \
    pip install --no-cache-dir -r watchdog/requirements.txt

# --- Final stage ---
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create a non-root user
RUN groupadd --gid 1001 pythonuser && \
    useradd --uid 1001 --gid 1001 --create-home pythonuser
USER pythonuser

# Copy installed packages from builder stage
COPY --from=builder --chown=pythonuser:pythonuser /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=pythonuser:pythonuser /usr/local/bin /usr/local/bin
# Copy the compiled requirements file for reference (optional)
COPY --from=builder --chown=pythonuser:pythonuser /app/watchdog/requirements.txt /app/watchdog/

# Copy application code
# Ensure this path is relative to the build context root
COPY --chown=pythonuser:pythonuser watchdog/app /app/app

# Set environment variables
ENV PYTHONPATH=/app
# No PORT needed for this service

# Run the application using python -m
CMD ["python", "-m", "app.main"]