import asyncio
import os # Ensure os is imported
from contextlib import asynccontextmanager
import importlib
import anyio # Import anyio
from spreadpilot_core.logging import get_logger # Import logger
from spreadpilot_core.utils.secrets import get_secret_from_mongo # Import secret getter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware # Add this

# Import modules using importlib - Keep these grouped
admin_api_api = importlib.import_module('admin_api.app.api.v1.api')
admin_api_config = importlib.import_module('admin_api.app.core.config')
admin_api_dashboard = importlib.import_module('admin_api.app.api.v1.endpoints.dashboard')
# admin_api_firestore = importlib.import_module('admin_api.app.db.firestore') # Removed Firestore import
admin_api_mongodb = importlib.import_module('admin_api.app.db.mongodb')


# --- Secret Pre-loading ---

logger = get_logger(__name__) # Initialize logger early for pre-loading

# Define secrets needed by this specific service (Add actual names as needed)
SECRETS_TO_FETCH = [
    # "ADMIN_API_KEY", # Example
    # "ANOTHER_SECRET"
]

async def load_secrets_into_env():
    """Fetches secrets from MongoDB and sets them as environment variables."""
    logger.info("Attempting to load secrets from MongoDB into environment variables...")
    # Need to import connect/close/get_db specifically for this function scope
    connect_mongo_preload = admin_api_mongodb.connect_to_mongo
    close_mongo_preload = admin_api_mongodb.close_mongo_connection
    get_db_preload = admin_api_mongodb.get_mongo_db
    db = None
    try:
        await connect_mongo_preload()
        db = await get_db_preload() # Get DB instance after connecting

        app_env = os.environ.get("APP_ENV", "development") # Determine environment

        for secret_name in SECRETS_TO_FETCH:
            logger.debug(f"Fetching secret: {secret_name} for env: {app_env}")
            secret_value = await get_secret_from_mongo(db, secret_name, environment=app_env)
            if secret_value is not None:
                os.environ[secret_name] = secret_value
                logger.info(f"Successfully loaded secret '{secret_name}' into environment.")
            else:
                # This might be expected if a secret is optional or env-specific
                logger.info(f"Secret '{secret_name}' not found in MongoDB for env '{app_env}'. Environment variable not set.")

        logger.info("Finished loading secrets into environment.")

    except Exception as e:
        logger.error(f"Failed to load secrets from MongoDB into environment: {e}", exc_info=True)
        # Depending on criticality, might raise error or proceed
    finally:
        # Ensure connection is closed regardless of success/failure
        if db is not None: # Check if connection was successful enough to get db
             await close_mongo_preload()


# Run secret loading BEFORE initializing settings or FastAPI app
# Skips if TESTING env var is set
if __name__ != "__main__" and not os.getenv("TESTING"):
    try:
        asyncio.run(load_secrets_into_env())
    except RuntimeError as e:
        # Handle cases where event loop is already running if necessary
        logger.error(f"Could not run async secret loading: {e}")
elif os.getenv("TESTING"):
     logger.info("TESTING environment detected, skipping MongoDB secret pre-loading.")


# --- Regular Application Setup ---

# Get specific imports (original imports resume here)
api_router = admin_api_api.api_router
get_settings = admin_api_config.get_settings
periodic_follower_update_task = admin_api_dashboard.periodic_follower_update_task
# get_firestore_client = admin_api_firestore.get_firestore_client # Replaced
connect_to_mongo = admin_api_mongodb.connect_to_mongo
close_mongo_connection = admin_api_mongodb.close_mongo_connection
get_mongo_db = admin_api_mongodb.get_mongo_db # Import the dependency getter

settings = get_settings() # Settings instance created AFTER env vars are potentially populated by load_secrets_into_env

# Store background tasks - Use a task group instead of a set (Keep existing logic)
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
            admin_api_follower_service = importlib.import_module('admin_api.app.services.follower_service')
            FollowerService = admin_api_follower_service.FollowerService
            follower_service_bg = FollowerService(db=db_instance, settings=settings) # Use db_instance

            # Start the periodic background task ONLY if not testing
            if not os.getenv("TESTING"):
                # Use start_soon for background tasks that run indefinitely
                task_group.start_soon(
                    periodic_follower_update_task,
                    follower_service_bg, # Pass the instantiated service
                    15 # interval_seconds
                )
                # Note: periodic_follower_update_task itself needs to be an async function
                # accepting (service, interval) as arguments.
            else:
                print("TESTING environment detected, skipping background task.") # Optional: for debugging

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