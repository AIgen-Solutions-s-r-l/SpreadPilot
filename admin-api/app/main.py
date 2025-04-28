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
admin_api_firestore = importlib.import_module('admin-api.app.db.firestore') # Keep for now, remove later
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
    admin_api_follower_service = importlib.import_module('admin-api.app.services.follower_service')
    # FollowerService = admin_api_follower_service.FollowerService # Instantiation moved inside task group
    # follower_service = FollowerService(db=db, settings=settings) # Instantiation moved

    # Use a task group to manage background tasks
    try:
        async with anyio.create_task_group() as task_group:
            # Instantiate FollowerService here, assuming it will use Depends(get_mongo_db) later
            # For the background task, we might need to pass the db instance explicitly if Depends isn't used directly
            # Let's assume for now the task itself will resolve the dependency or we adapt it later.
            # Placeholder: We need to figure out how periodic_follower_update_task gets its DB dependency.
            # For now, let's comment out the task start until FollowerService is refactored.
            # db_instance = await get_mongo_db() # Get DB instance for the task if needed
            # follower_service = FollowerService(db=db_instance, settings=settings) # Example if explicit passing needed

            # task_group._spawn( # Corrected method name and argument passing
            #     periodic_follower_update_task,
            #     follower_service, # Pass follower_service positionally
            #     15 # Pass interval_seconds positionally
            # )

            yield # Application starts here
    finally:
        # Close MongoDB connection on shutdown
        await close_mongo_connection()

    # Shutdown background tasks - Task group handles cancellation and waiting on exit
        # Start the periodic task
        task_group._spawn( # Corrected method name and argument passing
            periodic_follower_update_task,
            follower_service, # Pass follower_service positionally
            15 # Pass interval_seconds positionally
        )
        
        yield # Application starts here

    # Shutdown background tasks - Task group handles cancellation and waiting on exit
    # for task in background_tasks: # Removed
    #     task.cancel() # Removed
    
    # Wait for tasks to complete # Removed
    # await asyncio.gather(*background_tasks, return_exceptions=True) # Removed

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