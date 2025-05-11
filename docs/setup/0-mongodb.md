# MongoDB Setup Guide for SpreadPilot

This document provides detailed instructions for setting up MongoDB for the SpreadPilot trading system. It covers the initial setup, configuration, user creation, and verification steps.

## Prerequisites

- Docker and Docker Compose installed on your system
- Basic understanding of MongoDB concepts
- Access to the SpreadPilot repository

## 1. MongoDB Configuration in docker-compose.yml

The SpreadPilot system uses MongoDB as its primary database, configured in the `docker-compose.yml` file. Here's the relevant section:

```yaml
mongodb:
  image: mongo:7
  container_name: spreadpilot-mongodb
  environment:
    MONGO_INITDB_ROOT_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
    MONGO_INITDB_ROOT_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
  volumes:
    - mongo_data:/data/db
  ports:
    - "27017:27017" # Expose to host for potential direct access during dev
  restart: unless-stopped
  healthcheck:
    test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
    interval: 10s
    timeout: 10s
    retries: 5
    start_period: 40s
```

This configuration:
- Uses the official MongoDB 7.x image
- Names the container `spreadpilot-mongodb`
- Sets up environment variables for root username and password (loaded from `.env` file)
- Mounts a persistent volume for data storage
- Exposes port 27017 for direct access during development
- Configures automatic restart unless explicitly stopped
- Includes a healthcheck to verify MongoDB is running properly

## 2. Environment Variables Setup

MongoDB credentials are stored in the `.env` file at the project root. At minimum, you need to define:

```
# MongoDB
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password
```

**Important:** For production environments, use strong, unique passwords. The values shown here are for development purposes only.

## 3. Starting MongoDB

To start the MongoDB container:

```bash
docker-compose up -d mongodb
```

This command:
- Starts MongoDB in detached mode (`-d`)
- Uses the configuration from `docker-compose.yml`
- Creates and initializes the MongoDB container with the root user credentials from `.env`

## 4. Verifying MongoDB is Running

Check if MongoDB is running with:

```bash
docker ps | grep mongodb
```

You should see output similar to:

```
CONTAINER ID   IMAGE     COMMAND                  CREATED          STATUS                    PORTS                      NAMES
59e1188004c8   mongo:7   "docker-entrypoint.s…"   5 seconds ago    Up 4 seconds (healthy)    0.0.0.0:27017->27017/tcp   spreadpilot-mongodb
```

The `(healthy)` status indicates that MongoDB passed the healthcheck defined in the docker-compose file.

## 5. Connecting to MongoDB

To connect to MongoDB with the root user:

```bash
docker exec -it spreadpilot-mongodb mongosh admin --username admin --password password --authenticationDatabase admin
```

This command:
- Executes the MongoDB shell (`mongosh`) inside the running container
- Connects to the `admin` database
- Uses the root credentials specified in the `.env` file
- Specifies `admin` as the authentication database

If successful, you'll see the MongoDB shell prompt:

```
Current Mongosh Log ID: 681f5ec43174469589d861df
Connecting to:          mongodb://<credentials>@127.0.0.1:27017/admin?directConnection=true&serverSelectionTimeoutMS=2000&authSource=admin&appName=mongosh+2.5.0
Using MongoDB:          7.0.20
Using Mongosh:          2.5.0

For mongosh info see: https://www.mongodb.com/docs/mongodb-shell/

admin>
```

## 6. Creating Application Database and User

For security best practices, we create a dedicated database and user for the SpreadPilot application. This follows the principle of least privilege, ensuring the application has only the permissions it needs.

While connected to MongoDB with the root user, execute:

```javascript
// Switch to the application database
use spreadpilot

// Create a dedicated user for the application
db.createUser({
  user: "spreadpilot_user",
  pwd: "spreadpilot_password",
  roles: [ { role: "readWrite", db: "spreadpilot" } ]
})
```

This:
- Creates a new database called `spreadpilot` (MongoDB creates databases on-demand)
- Creates a new user `spreadpilot_user` with password `spreadpilot_password`
- Grants this user `readWrite` permissions only on the `spreadpilot` database

You should see `{ ok: 1 }` as the response, indicating success.

## 7. Verifying Application User Access

Exit the MongoDB shell by typing `exit`, then verify the application user can connect:

```bash
docker exec -it spreadpilot-mongodb mongosh spreadpilot --username spreadpilot_user --password spreadpilot_password --authenticationDatabase spreadpilot
```

This command:
- Connects directly to the `spreadpilot` database
- Uses the application-specific credentials
- Specifies `spreadpilot` as the authentication database

If successful, you'll see the MongoDB shell prompt for the spreadpilot database:

```
Current Mongosh Log ID: 681f5f4f5aef7b6241d861df
Connecting to:          mongodb://<credentials>@127.0.0.1:27017/spreadpilot?directConnection=true&serverSelectionTimeoutMS=2000&authSource=spreadpilot&appName=mongosh+2.5.0
Using MongoDB:          7.0.20
Using Mongosh:          2.5.0

For mongosh info see: https://www.mongodb.com/docs/mongodb-shell/

spreadpilot>
```

## 8. Troubleshooting

### Authentication Failures

If you encounter authentication failures:

1. Verify the credentials in your `.env` file match what you're using to connect
2. Ensure MongoDB has fully initialized (check logs with `docker logs spreadpilot-mongodb`)
3. If you've changed credentials, you may need to recreate the container:
   ```bash
   docker-compose down -v mongodb
   docker-compose up -d mongodb
   ```
   This removes the volume, ensuring a clean start with the new credentials.

### Connection Issues

If you can't connect to MongoDB:

1. Verify the container is running: `docker ps | grep mongodb`
2. Check container logs: `docker logs spreadpilot-mongodb`
3. Ensure port 27017 is not blocked by a firewall
4. Verify Docker networking is functioning correctly

## 9. Security Considerations for Production

For production environments:

1. Use strong, unique passwords for both root and application users
2. Consider using a secrets management solution rather than storing credentials in `.env`
3. Restrict network access to MongoDB (remove or restrict the port mapping)
4. Enable MongoDB authentication and TLS/SSL
5. Implement regular backups of the MongoDB data
6. Consider using MongoDB Atlas or another managed service for production deployments

## 10. Next Steps

After setting up MongoDB, you can proceed to configure other services in the SpreadPilot system, such as the Interactive Brokers Gateway, Trading Bot, and Admin API.

Each of these services will connect to MongoDB using the application user credentials you've created.