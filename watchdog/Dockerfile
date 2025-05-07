# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install pip-tools for compiling requirements.txt
RUN pip install pip-tools

# Copy the requirements files into the container at /app
COPY requirements.in /app/

# Compile requirements.in to requirements.txt and install dependencies
# This step leverages Docker layer caching. If requirements.in hasn't changed,
# this layer won't be rebuilt.
RUN pip-compile requirements.in -o requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . /app/

# Make port 80 available to the world outside this container (if needed for health checks, etc.)
# Adjust if the watchdog exposes an API or status endpoint.
# EXPOSE 80 

# Define environment variables (if any)
# ENV NAME="Watchdog"

# Run main.py when the container launches
CMD ["python", "main.py"]