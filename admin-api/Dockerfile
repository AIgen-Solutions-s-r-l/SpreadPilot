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

# Expose the port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]