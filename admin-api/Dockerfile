# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.in .

# Install any needed packages specified in requirements.in
RUN pip install --no-cache-dir -r requirements.in

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]