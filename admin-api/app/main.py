import asyncio
from contextlib import asynccontextmanager
import importlib
import anyio # Import anyio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import modules using importlib
admin_api_api = importlib.import_module('admin-api.app.api.v1.api')
admin_api_config = importlib.import_module('admin-api.app.core.config')
admin_api_dashboard = importlib.import_module('admin-api.app.api.v1.endpoints.dashboard')
# admin_api_firestore = importlib.import_module('admin-api.app.db.firestore') # Removed Firestore import
admin_api_mongodb = importlib.import_module('admin-api.app.db.mongodb')

# Get specific imports
api_router = admin_api_api.api_router
get_settings = admin_api_config.get_settings
periodic_follower_update_task = admin_api_dashboard.periodic_follower_update_task
# get_firestore_client = admin_api_firestore.get_firestore_client # Replaced
connect_to_mongo = admin_api_mongodb.connect_to_mongo
close_mongo_connection = admin_api_mongodb.close_mongo_connection
get_mongo_db = admin_api_mongodb.get_mongo_db # Import the dependency getter

settings = get_settings()

# Store background tasks - Use a task group instead of a set
# background_tasks = set() # Removed

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB on startup
    await connect_to_mongo()
    # db = get_firestore_client() # Removed Firestore client init

    # Create a follower service instance (will need db dependency update later)
    # For now, let's prepare the service import
    # Use a task group to manage background tasks
    try:
        async with anyio.create_task_group() as task_group:
            # Get DB instance for background task dependencies
            db_instance = await get_mongo_db()

            # Import and instantiate FollowerService for the background task
            admin_api_follower_service = importlib.import_module('admin-api.app.services.follower_service')
            FollowerService = admin_api_follower_service.FollowerService
            follower_service_bg = FollowerService(db=db_instance, settings=settings) # Use db_instance

            # Start the periodic background task
            # Use start_soon for background tasks that run indefinitely
            task_group.start_soon(
                periodic_follower_update_task,
                follower_service_bg, # Pass the instantiated service
                15 # interval_seconds
            )
            # Note: periodic_follower_update_task itself needs to be an async function
            # accepting (service, interval) as arguments.

            yield # Application runs while tasks are in the background
            # Task group automatically handles cancellation on exit from the 'with' block

    finally:
        # Close MongoDB connection on shutdown (ensures cleanup even if task group errors)
        await close_mongo_connection()

    # Removed duplicated/old shutdown logic below

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