import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.v1.endpoints.auth import User, get_current_user
from app.api.v1.endpoints.websocket import broadcast_update
from app.core.config import get_settings
from app.db.mongodb import get_db
from app.services.follower_service import FollowerService
from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


# Dashboard endpoints
@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get a summary of the dashboard data.
    """
    try:
        # Create follower service
        follower_service = FollowerService(db=db)

        # Get follower stats
        follower_count = await follower_service.get_follower_count()
        active_followers = await follower_service.get_active_follower_count()

        # Return summary
        return {
            "follower_stats": {
                "total": follower_count,
                "active": active_followers,
                "inactive": follower_count - active_followers,
            },
            "system_status": "operational",
        }
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting dashboard summary: {e!s}",
        )


# Background task to periodically update follower data
async def periodic_follower_update_task(follower_service: FollowerService):
    """
    Background task to periodically update follower data and broadcast updates.
    """
    logger.info("Starting periodic follower update task")
    try:
        while True:
            # Wait for the specified interval
            await asyncio.sleep(settings.follower_update_interval)

            try:
                # Update follower data
                logger.debug("Updating follower data...")
                follower_count = await follower_service.get_follower_count()
                active_followers = await follower_service.get_active_follower_count()

                # Broadcast update to WebSocket clients
                await broadcast_update(
                    {
                        "type": "follower_update",
                        "data": {
                            "total": follower_count,
                            "active": active_followers,
                            "inactive": follower_count - active_followers,
                        },
                    }
                )

                logger.debug("Follower data updated and broadcast")
            except Exception as e:
                logger.error(f"Error in follower update task: {e}")
                # Continue the loop even if there's an error
    except asyncio.CancelledError:
        logger.info("Follower update task cancelled")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in follower update task: {e}")
        raise
