from typing import List
import importlib

from fastapi import APIRouter, Depends, HTTPException, status
# from google.cloud import firestore # Removed Firestore import
from motor.motor_asyncio import AsyncIOMotorDatabase # Added MongoDB import

from spreadpilot_core.logging.logger import get_logger

# Import modules using importlib
admin_api_config = importlib.import_module('admin_api.app.core.config')
admin_api_db = importlib.import_module('admin_api.app.db.mongodb') # Changed to mongodb
admin_api_schemas = importlib.import_module('admin_api.app.schemas.follower')
admin_api_services = importlib.import_module('admin_api.app.services.follower_service')

# Get specific imports
Settings = admin_api_config.Settings
get_settings = admin_api_config.get_settings
get_mongo_db = admin_api_db.get_mongo_db # Changed to get_mongo_db
FollowerCreate = admin_api_schemas.FollowerCreate
FollowerRead = admin_api_schemas.FollowerRead
FollowerService = admin_api_services.FollowerService

logger = get_logger(__name__)

router = APIRouter()

# Dependency to get the FollowerService instance, using MongoDB
def get_follower_service(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db), # Changed dependency and type hint
    settings: Settings = Depends(get_settings)
) -> FollowerService:
    # Pass MongoDB db and settings to the service constructor
    return FollowerService(db=db, settings=settings)


@router.get(
    "/followers",
    response_model=List[FollowerRead],
    summary="List All Followers",
    description="Retrieves a list of all registered followers.",
)
async def list_followers(
    follower_service: FollowerService = Depends(get_follower_service),
):
    """
    Retrieve all followers.
    """
    try:
        followers = await follower_service.get_followers()
        return followers
    except Exception as e:
        logger.error(f"Error retrieving followers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve followers.",
        )


@router.post(
    "/followers",
    response_model=FollowerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Follower",
    description="Registers a new follower in the system.",
)
async def create_follower(
    follower_in: FollowerCreate,
    follower_service: FollowerService = Depends(get_follower_service),
):
    """
    Create a new follower.
    """
    try:
        # Basic check for existing email could be added here if needed
        # follower = await follower_service.get_follower_by_email(follower_in.email)
        # if follower:
        #     raise HTTPException(...)
        
        new_follower = await follower_service.create_follower(follower_in)
        return new_follower
    except ValueError as ve: # Catch validation errors from Pydantic/Core model
        logger.warning(f"Follower creation validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Error creating follower: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create follower.",
        )


@router.post(
    "/followers/{follower_id}/toggle",
    response_model=FollowerRead,
    summary="Toggle Follower Enabled Status",
    description="Enables or disables a specific follower.",
)
async def toggle_follower(
    follower_id: str,
    follower_service: FollowerService = Depends(get_follower_service),
):
    """
    Toggle the enabled status of a follower by ID.
    """
    try:
        updated_follower = await follower_service.toggle_follower_enabled(follower_id)
        if updated_follower is None:
            logger.warning(f"Attempted to toggle non-existent follower: {follower_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Follower with ID '{follower_id}' not found.",
            )
        return updated_follower
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (like the 404) directly
        raise http_exc
    except Exception as e:
        # Catch other unexpected errors and return 500
        logger.error(f"Unexpected error toggling follower {follower_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred while toggling follower status.", # Generic message for 500
        )


@router.post(
    "/close/{follower_id}", # Removed redundant /api/v1 prefix
    status_code=status.HTTP_202_ACCEPTED, # Accepted, as the action is asynchronous
    summary="Trigger Close Positions for Follower",
    description="Sends a command to the trading bot to close all positions for a specific follower.",
)
async def trigger_close_positions(
    follower_id: str,
    follower_service: FollowerService = Depends(get_follower_service),
):
    """
    Trigger the close positions command for a follower by ID.
    """
    # First, check if follower exists
    follower = await follower_service.get_follower_by_id(follower_id)
    if follower is None:
        logger.warning(f"Attempted to close positions for non-existent follower: {follower_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Follower with ID '{follower_id}' not found.",
        )
        
    try:
        # Call the service method (which currently contains placeholder logic)
        success = await follower_service.trigger_close_positions(follower_id)
        if not success:
            # This might indicate an issue communicating with the trading-bot
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Or 500 depending on expected failure modes
                detail=f"Failed to trigger close positions for follower {follower_id}. Trading bot might be unavailable or encountered an error.",
            )
        
        # Optionally update follower state after successful trigger
        # await follower_service.update_follower_state(follower_id, FollowerState.MANUAL_INTERVENTION)

        return {"message": f"Close positions command accepted for follower {follower_id}."}
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions from the service call if any
        raise http_exc
    except Exception as e:
        logger.error(f"Error triggering close positions for follower {follower_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger close positions for follower {follower_id}.",
        )