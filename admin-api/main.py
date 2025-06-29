from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
import os

# Import the main API router
from app.api.v1.api import api_router
from spreadpilot_core.logging.logger import setup_logging, get_logger
from app.core.config import get_settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.services.follower_service import FollowerService
from app.api.v1.endpoints.dashboard import periodic_follower_update_task

# Setup logging from the core library
setup_logging(service_name="admin-api")
logger = get_logger(__name__)

# Get settings instance
settings = get_settings()

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    
    # Initialize MongoDB connection
    await connect_to_mongo()
    
    # Initialize dependencies needed for the background task
    follower_service = FollowerService()
    
    # Create and start the background task
    update_task = asyncio.create_task(periodic_follower_update_task(follower_service))
    logger.info("Periodic follower update task started.")
    
    yield # Application runs here
    
    # Application shutdown
    logger.info("Application shutdown...")
    update_task.cancel()
    try:
        await update_task # Wait for task cancellation
    except asyncio.CancelledError:
        logger.info("Periodic follower update task cancelled successfully.")
    
    # Close MongoDB connection
    await close_mongo_connection()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="SpreadPilot Admin API",
    description="""
API service for managing SpreadPilot followers and operations.

## Features

* **Authentication**: JWT-based authentication for all endpoints
* **Followers Management**: CRUD operations for follower accounts
* **P&L Tracking**: Real-time profit and loss data (daily and monthly)
* **Logs Access**: Query system logs with filtering capabilities
* **Manual Operations**: Emergency position closing with PIN verification (PIN: 0312)
* **WebSocket**: Real-time updates for dashboard
* **Health Monitoring**: Service health check endpoint

## Security

All endpoints (except /health) require JWT authentication. 
Manual operations additionally require PIN verification.
    """,
    version="0.2.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Authentication", "description": "Login and token management"},
        {"name": "Dashboard", "description": "Dashboard data and updates"},
        {"name": "Followers", "description": "Follower account management"},
        {"name": "P&L", "description": "Profit and Loss data endpoints"},
        {"name": "Logs", "description": "System log access"},
        {"name": "Manual Operations", "description": "Manual trading operations (requires PIN)"},
        {"name": "WebSocket", "description": "Real-time WebSocket connections"},
        {"name": "Health", "description": "Service health monitoring"},
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    # Use origins from settings, split comma-separated string into a list
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(',')] if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}

# Include the main API router using prefix from settings
app.include_router(api_router, prefix=settings.api_v1_prefix)

if __name__ == "__main__":
    import uvicorn
    # The port 8080 is chosen to match the docker-compose configuration
    uvicorn.run(app, host="0.0.0.0", port=8080)