#!/usr/bin/env python3
"""
Admin API - FastAPI application with JWT authentication for SpreadPilot.
This module provides a dedicated admin API with Traefik integration.
"""

import asyncio
import os
from contextlib import asynccontextmanager

# Import the main API router and authentication
from app.api.v1.api import api_router
from app.api.v1.endpoints.auth import User, get_current_user
from app.api.v1.endpoints.dashboard import periodic_follower_update_task
from app.core.config import get_settings
from app.db.mongodb import close_mongo_connection, connect_to_mongo
from app.services.follower_service import FollowerService
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from spreadpilot_core.logging.logger import get_logger, setup_logging

# Setup logging
setup_logging(service_name="admin-api")
logger = get_logger(__name__)

# Get settings instance
settings = get_settings()

# Background task reference
background_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    Handles MongoDB connection and background tasks.
    """
    global background_task

    logger.info("Admin API startup...")

    # Initialize MongoDB connection
    await connect_to_mongo()
    logger.info("MongoDB connection established")

    # Initialize dependencies for background task
    follower_service = FollowerService()

    # Create and start the background task
    background_task = asyncio.create_task(periodic_follower_update_task(follower_service))
    logger.info("Periodic follower update task started")

    yield  # Application runs here

    # Application shutdown
    logger.info("Admin API shutdown...")

    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("Background task cancelled successfully")
    # Close MongoDB connection
    await close_mongo_connection()
    logger.info("Admin API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="SpreadPilot Admin API",
    description="JWT-secured admin API for SpreadPilot trading platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [origin.strip() for origin in settings.cors_origins.split(",")]
        if settings.cors_origins
        else ["*"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Custom HTTP exception handler for consistent error responses.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint providing API information.
    """
    return {
        "name": "SpreadPilot Admin API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    try:
        # Check MongoDB connection
        from app.db.mongodb import get_database

        db = await get_database()
        await db.command("ping")

        return {
            "status": "healthy",
            "service": "admin-api",
            "mongodb": "connected",
            "background_task": (
                "running" if background_task and not background_task.done() else "stopped"
            ),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "admin-api",
                "error": str(e),
            },
        )


@app.get("/protected", tags=["Auth"])
async def protected_route(current_user: User = Depends(get_current_user)):
    """
    Example protected endpoint requiring JWT authentication.
    """
    return {
        "message": "This is a protected route",
        "user": current_user.username,
    }


# Include the main API router with authentication
app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
    tags=["API v1"],
)


# Traefik-specific health check endpoint
@app.get("/ping", tags=["Health"])
async def traefik_ping():
    """
    Lightweight ping endpoint for Traefik health checks.
    """
    return {"ping": "pong"}


if __name__ == "__main__":
    import uvicorn

    # Run with environment-based configuration
    port = int(os.getenv("ADMIN_API_PORT", "8002"))
    host = os.getenv("ADMIN_API_HOST", "0.0.0.0")
    reload = os.getenv("ADMIN_API_RELOAD", "false").lower() == "true"

    logger.info(f"Starting Admin API on {host}:{port}")

    uvicorn.run(
        "admin_api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
