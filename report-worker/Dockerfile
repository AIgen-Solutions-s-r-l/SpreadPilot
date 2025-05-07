# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Set the working directory in the container
WORKDIR /app

# Install pip-tools for compiling requirements
RUN pip install --no-cache-dir --upgrade pip pip-tools

# --- Install dependencies ---
# Copy the core library source into the image (Path relative to project root context '.')
COPY ./spreadpilot-core /app/spreadpilot-core
# Copy the requirements file (Path relative to project root context '.')
COPY ./report-worker/requirements.in /app/requirements.in
# Compile requirements.in to requirements.txt and install
RUN pip-compile requirements.in -o requirements.txt --resolver=backtracking \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container (Path relative to project root context '.')
COPY ./report-worker/app /app/app

# Set environment variables
ENV PYTHONPATH=/app
# Assuming report-worker might need a port, though it's a worker.
# If it's triggered by events, a port might not be needed.
# For now, setting a default port similar to others.
ENV PORT=8084

# Expose port (if needed)
EXPOSE 8084

# Define the command to run the application
# Assuming main.py is the entry point
CMD ["python", "app/main.py"]