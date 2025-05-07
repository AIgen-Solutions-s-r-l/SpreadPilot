# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED True
ENV APP_HOME /app

# Set the working directory in the container
WORKDIR $APP_HOME

# Install system dependencies that might be needed by Python packages
# (e.g., build tools, or libraries needed by reportlab for PDF generation)
# Adjust as necessary based on spreadpilot-core dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    # Add other dependencies if needed, e.g., libjpeg-dev zlib1g-dev for Pillow/ReportLab
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY ./report-worker/requirements.in ./

# Install project dependencies
# First, install pip-tools
RUN pip install --no-cache-dir pip-tools

# Compile requirements.in to requirements.txt
# This ensures consistent dependencies based on the .in file
# We copy spreadpilot-core later, so we use --allow-unsafe here if needed,
# or handle core installation separately. Let's assume core is handled via the -e flag.
# Copy the spreadpilot-core library source code into the container
# This assumes spreadpilot-core is one level up from the project root (build context)
# The destination is /app/spreadpilot-core inside the container
COPY ./spreadpilot-core /app/spreadpilot-core

RUN pip-compile requirements.in --output-file requirements.txt --allow-unsafe

# Install the compiled dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Install spreadpilot-core in editable mode (or regular install if preferred)
# This makes the `-e ../spreadpilot-core` in requirements.txt work
RUN pip install --no-cache-dir -e ./spreadpilot-core

# Copy the application code into the container
COPY ./report-worker/app ./app

# Specify the command to run on container startup
# Use gunicorn for a production-ready WSGI server
# Install gunicorn first
RUN pip install --no-cache-dir gunicorn

# Expose the port the app runs on (should match PORT env var, default 8080)
EXPOSE 8080

# Run the web server
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app.main:app