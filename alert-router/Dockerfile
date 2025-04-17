# Use an official Python runtime as a parent image
FROM python:3.10-slim

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

# --- Install spreadpilot-core ---
# Copy the core library source into the image
# Assumes the Docker build context is the project root (../)
COPY ./spreadpilot-core /app/spreadpilot-core
# Install the core library in editable mode
# This makes its modules available to the alert-router app
RUN pip install --no-cache-dir -e /app/spreadpilot-core

# --- Install alert-router dependencies ---
# Copy the requirements file
COPY ./alert-router/requirements.in /app/requirements.in
# Compile requirements.in to requirements.txt and install
# This ensures deterministic builds using pinned versions
RUN pip-compile requirements.in -o requirements.txt --resolver=backtracking \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./alert-router/app /app/app

# Expose the port the app runs on
EXPOSE 8080

# Define the command to run the application
# Use the PORT environment variable provided by Cloud Run, default to 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}"]