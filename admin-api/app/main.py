import asyncio
from contextlib import asynccontextmanager
import importlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import modules using importlib
admin_api_api = importlib.import_module('admin-api.app.api.v1.api')
admin_api_config = importlib.import_module('admin-api.app.core.config')
admin_api_dashboard = importlib.import_module('admin-api.app.api.v1.endpoints.dashboard')
admin_api_firestore = importlib.import_module('admin-api.app.db.firestore')

# Get specific imports
api_router = admin_api_api.api_router
get_settings = admin_api_config.get_settings
periodic_follower_update_task = admin_api_dashboard.periodic_follower_update_task
get_firestore_client = admin_api_firestore.get_firestore_client

settings = get_settings()

# Store background tasks
background_tasks = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    db = get_firestore_client()
    
    # Create a follower service instance
    admin_api_follower_service = importlib.import_module('admin-api.app.services.follower_service')
    FollowerService = admin_api_follower_service.FollowerService
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