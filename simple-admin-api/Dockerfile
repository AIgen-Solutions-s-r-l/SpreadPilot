FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] pymongo pydantic python-jose[cryptography] passlib[bcrypt] python-multipart websockets

# Copy application code
COPY app.py .

# Expose the port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]