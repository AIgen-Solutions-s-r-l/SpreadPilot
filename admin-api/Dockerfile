# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file for admin-api from the build context
COPY admin-api/requirements.in .

# Copy the local dependency spreadpilot-core from the build context
COPY spreadpilot-core/ ./spreadpilot-core/

# Install any needed packages specified in requirements.in
# This should now find spreadpilot-core in ./spreadpilot-core within the container
RUN pip install --no-cache-dir -r requirements.in

# Copy the rest of the admin-api application code from the build context
COPY admin-api/ .

# Expose the port the app runs on
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]