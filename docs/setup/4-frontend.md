# 🖥️ Frontend Setup Guide for SpreadPilot

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [1. Understanding the Frontend](#1-understanding-the-frontend)
- [2. Docker Configuration](#2-frontend-configuration-in-docker-composeyml)
- [3. Environment Variables](#3-environment-variables-setup)
- [4. Starting the Service](#4-starting-the-frontend)
- [5. Health Verification](#5-verifying-the-frontend-is-running)
- [6. Browser Access](#6-accessing-the-frontend)
- [7. Development Setup](#7-local-development)
- [8. Production Build](#8-building-for-production)
- [9. Troubleshooting](#9-troubleshooting)
- [10. Security](#10-security-considerations)
- [11. Customization](#11-customization)
- [12. Next Steps](#12-next-steps)

## 📖 Overview

This document provides detailed instructions for setting up the Frontend for the SpreadPilot system. It covers the configuration, startup, verification, and troubleshooting steps.

> 💡 **Quick Setup**: For a simplified setup process, refer to the [FRONTEND-SETUP.md](../../FRONTEND-SETUP.md) file in the project root. It provides a Docker-based approach for running the Frontend with minimal configuration.

## ✅ Prerequisites

- Docker and Docker Compose installed on your system
- Admin API service set up and running (see [Admin API Setup Guide](./3-admin-api.md))
- Node.js and npm installed on your system (for local development)
- Basic understanding of React and web development

## 1. 🎯 Understanding the Frontend

The Frontend is a web-based user interface for the SpreadPilot trading system.

### 🔧 Core Features

1. Providing a login interface for administrators
2. Displaying a dashboard with trading statistics and follower status
3. Allowing administrators to manage followers (enable/disable, view details)
4. Providing interfaces for viewing logs and issuing manual commands
5. Communicating with the Admin API for data and actions

### 🏗️ Technology Stack

The Frontend is implemented as a React application that runs in a Docker container. It communicates with the Admin API for data and actions.

- **Framework**: React with TypeScript
- **State Management**: React Context API
- **UI Components**: Material-UI
- **Real-time Updates**: WebSocket connections
- **Containerization**: Docker with Nginx

## 2. 🐳 Frontend Configuration in docker-compose.yml

The SpreadPilot system uses a containerized version of the Frontend, configured in the `docker-compose.yml` file. Here's the relevant section:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: spreadpilot-frontend
  environment:
    - REACT_APP_API_URL=http://admin-api:8080
    - REACT_APP_WS_URL=ws://admin-api:8080/ws
  depends_on:
    - admin-api
  ports:
    - "8080:80"
  restart: unless-stopped
```

This configuration:
- Builds the Frontend from the Dockerfile in the `frontend` directory
- Names the container `spreadpilot-frontend`
- Sets environment variables for the Admin API URL and WebSocket URL
- Specifies a dependency on the Admin API
- Exposes port 8080 on the host, mapping to port 80 in the container
- Configures automatic restart unless explicitly stopped

## 3. 🔐 Environment Variables Setup

The Frontend requires several environment variables to be set in the `.env` file at the project root. Here are the key variables:

```
# Frontend Configuration
REACT_APP_API_URL=http://localhost:8083
REACT_APP_WS_URL=ws://localhost:8083/ws
```

Replace the placeholder values with your actual settings if needed.

### ⚠️ Important Notes
- The `REACT_APP_API_URL` should point to the Admin API URL
- The `REACT_APP_WS_URL` should point to the Admin API WebSocket URL
- For local development, these should point to the host machine's ports (e.g., `localhost:8083`)
- For production environments, these should point to the appropriate domain or IP address

## 4. 🚀 Starting the Frontend

To start the Frontend container:

```bash
docker-compose up -d frontend
```

This command:
- Starts the Frontend in detached mode (`-d`)
- Uses the configuration from `docker-compose.yml`
- Creates and initializes the Frontend container with the environment variables from `.env`
- Automatically starts the required dependencies (Admin API) if they're not already running

## 5. ✔️ Verifying the Frontend is Running

Check if the Frontend container is running with:

```bash
docker ps | grep frontend
```

You should see output similar to:

```
CONTAINER ID   IMAGE                    COMMAND                  CREATED          STATUS          PORTS                    NAMES
abcdef123456   spreadpilot-frontend     "nginx -g 'daemon of…"   5 minutes ago    Up 5 minutes    0.0.0.0:8080->80/tcp     spreadpilot-frontend
```

## 6. 🌐 Accessing the Frontend

Once the Frontend container is running, you can access it in your web browser at:

```
http://localhost:8080
```

You should see the SpreadPilot login page. You can log in using the admin credentials you set up in the Admin API configuration.

## 7. 💻 Local Development

For local development, you can run the Frontend directly on your machine without Docker.

### 🛠️ Development Setup

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file with the following content:
   ```
   REACT_APP_API_URL=http://localhost:8083
   REACT_APP_WS_URL=ws://localhost:8083/ws
   ```

4. Start the development server:
   ```bash
   npm start
   ```

5. The development server will start and open the Frontend in your default browser at `http://localhost:3000`.

## 8. 🎭 Building for Production

To build the Frontend for production:

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Build the application:
   ```bash
   npm run build
   ```

3. The build artifacts will be stored in the `build` directory.

## 9. 🔧 Troubleshooting

### 🔌 Connection Issues with Admin API

If the Frontend fails to connect to the Admin API:

1. Verify that the Admin API container is running: `docker ps | grep admin-api`
2. Check that the `REACT_APP_API_URL` and `REACT_APP_WS_URL` environment variables are set correctly
3. Check the Frontend logs for specific error messages: `docker logs spreadpilot-frontend`
4. Try accessing the Admin API directly to ensure it's responding: `curl http://localhost:8083/`

### 🔑 Login Issues

If you're having trouble logging in to the Frontend:

1. Verify that the Admin API is properly configured with the correct admin credentials
2. Check that the `JWT_SECRET` environment variable is set correctly in the Admin API configuration
3. Check the browser console for specific error messages
4. Try clearing your browser cache and cookies

### 🐳 Container Startup Issues

If the Frontend container fails to start:

1. Check Docker logs: `docker logs spreadpilot-frontend`
2. Verify that all required environment variables are set in the `.env` file
3. Ensure that the Admin API is running
4. Check system resources (CPU, memory, disk space)

## 10. 🔒 Security Considerations

For production environments:

1. Use HTTPS for the Frontend (e.g., using a reverse proxy like Nginx with SSL certificates)
2. Implement proper authentication and authorization
3. Consider using a Content Security Policy (CSP) to prevent XSS attacks
4. Regularly update dependencies to patch security vulnerabilities
5. Implement rate limiting to prevent brute force attacks
6. Consider implementing two-factor authentication for additional security

## 11. 🎨 Customization

The Frontend can be customized to match your organization's branding and requirements.

### 🎯 Customization Options

1. **Theme:** Modify the theme colors in `frontend/src/index.css`
2. **Logo:** Replace the logo file in `frontend/src/assets/`
3. **Layout:** Modify the layout components in `frontend/src/components/layout/`
4. **Pages:** Add or modify pages in `frontend/src/pages/`

## 12. ⏭️ Next Steps

After setting up the Frontend, your SpreadPilot system should be fully operational.

### 🚀 Ready to Use

1. Log in to the Frontend
2. Monitor trading activity on the dashboard
3. Manage followers
4. View logs
5. Issue manual commands

### 📚 Additional Resources

- [Operations Guide](../04-operations-guide.md) - For ongoing maintenance and operations
- [Development Guide](../03-development-guide.md) - For extending functionality
- [System Architecture](../01-system-architecture.md) - For understanding the overall system