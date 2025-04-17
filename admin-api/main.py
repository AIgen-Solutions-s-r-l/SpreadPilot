from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager

# Import the main API router
from app.api.v1.api import api_router
from spreadpilot_core.logging.logger import setup_logging, get_logger # Add get_logger
from app.core.config import get_settings
from app.db.firestore import get_db, get_firestore_client # Add get_firestore_client
from app.services.follower_service import FollowerService # Add FollowerService
from app.api.v1.endpoints.dashboard import periodic_follower_update_task # Add task import

# Setup logging from the core library
setup_logging()
logger = get_logger(__name__) # Get logger instance for lifespan

# Get settings instance
settings = get_settings()

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    # Initialize dependencies needed for the background task
    db_client = get_firestore_client() # Get client directly
    settings_instance = get_settings()
    follower_service = FollowerService(db=db_client, settings=settings_instance)
    
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
    # Add any other cleanup here if needed (e.g., close DB connections if not handled by client)
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="SpreadPilot Admin API",
    description="API service for managing SpreadPilot followers and operations.",
    version="0.1.0", # Remove duplicate version line
    lifespan=lifespan, # Add the lifespan manager
)

# Configure CORS (adjust origins as needed for your frontend)
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

# WebSocket endpoint is included via the api_router

if __name__ == "__main__":
    import uvicorn
    # Note: Run with `uvicorn admin-api.main:app --reload --host 0.0.0.0 --port 8001`
    # The port 8001 is chosen to avoid conflict with other potential services (e.g., trading-bot on 8000)
    uvicorn.run(app, host="0.0.0.0", port=8001)