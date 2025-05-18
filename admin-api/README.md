# SpreadPilot Admin API

This is the Admin API for the SpreadPilot trading system. It provides endpoints for managing followers, viewing dashboard data, and more.

## Features

- RESTful API with FastAPI
- MongoDB integration with Motor (async)
- JWT authentication
- WebSocket support for real-time updates
- Follower management (CRUD operations)
- Dashboard with real-time updates

## Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password
MONGO_DB_NAME=spreadpilot_admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=your_bcrypt_hash
JWT_SECRET=your_secret_key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

You can generate a bcrypt hash using the provided `generate_hash.py` script:

```bash
python generate_hash.py your_password
```

### Running with Docker Compose

```bash
docker-compose up -d
```

This will start the MongoDB database and the Admin API service.

### Local Development

1. Install dependencies:

```bash
pip install -e .
pip install -r requirements.txt
```

2. Run the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

## API Documentation

Once the API is running, you can access the Swagger documentation at:

```
http://localhost:8083/docs
```

## Authentication

To authenticate, make a POST request to `/api/v1/auth/token` with your username and password. This will return a JWT token that you can use for subsequent requests.

Example:

```bash
curl -X POST "http://localhost:8083/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password"
```

## WebSocket

Connect to the WebSocket endpoint at `/api/v1/ws/dashboard` to receive real-time updates about follower data.

## Testing

To run tests:

```bash
pytest