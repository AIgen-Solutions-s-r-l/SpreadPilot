import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin_api.app.api.v1.api import api_router
from admin_api.app.core.config import get_settings
from admin_api.app.api.v1.endpoints.dashboard import periodic_follower_update_task
from admin_api.app.db.firestore import get_firestore_client

settings = get_settings()

# Store background tasks
background_tasks = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    db = get_firestore_client()
    
    # Create a follower service instance
    from admin_api.app.services.follower_service import FollowerService
    follower_service = FollowerService(db=db, settings=settings)
    
    # Start the periodic task
    task = asyncio.create_task(periodic_follower_update_task(
        follower_service=follower_service,
        interval_seconds=15
    ))
    background_tasks.add(task)
    
    yield
    
    # Shutdown background tasks
    for task in background_tasks:
        task.cancel()
    
    # Wait for tasks to complete
    await asyncio.gather(*background_tasks, return_exceptions=True)

app = FastAPI(
    title="SpreadPilot Admin API",
    description="Admin API for SpreadPilot trading system",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to SpreadPilot Admin API"}

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}