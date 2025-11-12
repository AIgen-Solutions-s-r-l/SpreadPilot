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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install pip-tools for compiling requirements
RUN pip install --no-cache-dir --upgrade pip pip-tools

# --- Install dependencies ---
# Copy the core library source into the image
COPY ./spreadpilot-core /app/spreadpilot-core
# Install the core library in editable mode
RUN pip install --no-cache-dir -e /app/spreadpilot-core

# Copy the requirements file
COPY ./report-worker/requirements.in /app/requirements.in
# Install compatible pip-tools version and compile requirements
RUN pip install --no-cache-dir --upgrade "pip>=24.0" "pip-tools>=7.4.0" \
    && pip-compile requirements.in -o requirements.txt --resolver=backtracking \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./report-worker/app /app/app

# Copy crontab file
COPY ./report-worker/crontab /etc/cron.d/commission-reports
RUN chmod 0644 /etc/cron.d/commission-reports

# Create log directory for cron jobs
RUN mkdir -p /var/log && touch /var/log/commission_reports.log

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8084

# Install gunicorn for production-ready WSGI server
RUN pip install --no-cache-dir gunicorn

# Expose port
EXPOSE 8084

# Define the command to run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app.main:app