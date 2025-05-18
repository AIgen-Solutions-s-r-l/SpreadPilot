+++
id = "TASK-FRONTEND-WEBSOCKET-FIX"
title = "Fix WebSocket Connection in Frontend"
type = "🐞 Bug"
status = "🟢 Done"
priority = "🔴 High"
assigned_to = "dev-react"
coordinator = "roo-commander"
created_date = "2025-05-18"
updated_date = "2025-05-18" # Updated after applying fix
related_docs = [
  "FRONTEND-SETUP.md",
  "docker-compose.frontend.yml",
  ".env.frontend"
]
tags = ["frontend", "websocket", "bug", "connectivity"]
+++

# Fix WebSocket Connection in Frontend

## Description

The frontend is currently unable to connect to the WebSocket endpoint provided by the Admin API. The console shows the following errors:

```
Attempting to connect WebSocket to ws://localhost:8080/api/v1/ws
WebSocket connection to 'ws://localhost:8080/api/v1/ws' failed
WebSocket Error: Event
WebSocket Disconnected: 1006
```

The issue is that the frontend is trying to connect to `ws://localhost:8080/api/v1/ws`, but our WebSocket endpoint is at `ws://localhost:8083/ws`. 

## Acceptance Criteria

- [✅] Identify the source of the incorrect WebSocket URL in the frontend code
- [✅] Update the frontend code to use the correct WebSocket URL (`ws://localhost:8083/ws`)
- [✅] Ensure the environment variables are correctly passed to the frontend
- [✅] Verify that the WebSocket connection is established successfully
- [✅] Update any documentation as needed

## Technical Details

1. The Admin API provides a WebSocket endpoint at `/ws` (not at `/api/v1/ws`)
2. The Admin API is running on port 8083 (not 8080)
3. The environment variables for the frontend are defined in `.env.frontend`:
   ```
   REACT_APP_API_URL=http://localhost:8083
   REACT_APP_WS_URL=ws://localhost:8083/ws
   ```
4. The frontend is built using React and is running in a Docker container

## Implementation Notes

1. Check how the WebSocket URL is constructed in the frontend code
2. Ensure that the environment variables are correctly passed to the frontend during the build process
3. Consider adding a configuration file or environment variable check to make the WebSocket URL configurable
4. Test the WebSocket connection after making the changes

## Progress Notes

- Updated `frontend/src/App.tsx` to use `import.meta.env.REACT_APP_WS_URL`.
- Modified `frontend/Dockerfile` to copy `.env.frontend` into the build context.
- Confirmed `docker-compose.frontend.yml` passes the correct environment variables.
- **Critical Issue Found:** After investigating the backend code, discovered that the WebSocket endpoint at `/ws` was not implemented in the admin-api.
- **Implemented WebSocket Endpoint:** Added a WebSocket endpoint at `/ws` in the admin-api with the following features:
  - Connection management for multiple clients
  - JSON message parsing and validation
  - Echo functionality for testing
  - Broadcast capability for future enhancements
- **Next Steps for Verification:**
  1. Rebuild and run the admin-api container: `docker-compose -f docker-compose.admin-api.yml up -d --build`
  2. Rebuild and run the frontend container to verify the connection
- **Resolution:** The WebSocket connection issue has been resolved by:
  1. Installing the necessary WebSocket libraries in the Admin API container (`uvicorn[standard]` and `websockets`)
  2. Rebuilding and restarting the Admin API container
  3. Restarting the Frontend container
- **Verification:** The WebSocket endpoint is now properly recognized and responding at `ws://localhost:8083/ws`

## Resources

- [Frontend Setup Guide](../../FRONTEND-SETUP.md)
- [Docker Compose Frontend](../../docker-compose.frontend.yml)
- [Frontend Environment Variables](../../.env.frontend)