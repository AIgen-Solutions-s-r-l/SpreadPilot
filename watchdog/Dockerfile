# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install Docker CLI (needed for restart functionality)
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements files into the container at /app
COPY watchdog/requirements.in ./

# Install compatible pip-tools version and compile requirements
# This step leverages Docker layer caching. If requirements.in hasn't changed,
# this layer won't be rebuilt.
RUN pip install --no-cache-dir --upgrade "pip>=24.0" "pip-tools>=7.4.0" && \
    pip-compile requirements.in -o requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy spreadpilot-core library
COPY spreadpilot-core /app/spreadpilot-core
RUN pip install -e /app/spreadpilot-core

# Copy the rest of the application code into the container at /app
COPY watchdog/ .

# Create a non-root user to run the application
# Note: User needs to be in docker group to access docker.sock
RUN groupadd -r watchdog && useradd -r -g watchdog -u 1000 watchdog && \
    groupadd -g 999 docker || true && \
    usermod -aG docker watchdog

# Change ownership of the app directory
RUN chown -R watchdog:watchdog /app

# Switch to the non-root user
USER watchdog

# Make port 80 available to the world outside this container (if needed for health checks, etc.)
# Adjust if the watchdog exposes an API or status endpoint.
# EXPOSE 80 

# Define environment variables (if any)
# ENV NAME="Watchdog"

# Run main.py when the container launches
CMD ["python", "main.py"]