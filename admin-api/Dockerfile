FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.in .
RUN pip install --no-cache-dir pip-tools && \
    pip-compile requirements.in && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]