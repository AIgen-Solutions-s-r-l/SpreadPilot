from datetime import datetime

import pytz
from app.api.v1.endpoints.auth import get_current_user
from app.core.config import get_settings
from fastapi import APIRouter, Body, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from spreadpilot_core.db.mongodb import get_mongo_db
from spreadpilot_core.ibkr.client import IBKRClient
from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)



class ManualCloseRequest(BaseModel):
    follower_id: str = Field(
        ..., description="ID of the follower to close positions for"
    )
    pin: str = Field(..., description="Security PIN for manual operations")
    close_all: bool = Field(
        default=True, description="Close all positions or specific ones"
    )
    position_ids: list[str] | None = Field(
        default=None,
        description="Specific position IDs to close (if close_all is False)",
    )
    reason: str | None = Field(
        default="Manual close requested by admin", description="Reason for manual close"
    )


class ManualCloseResponse(BaseModel):
    success: bool
    message: str
    closed_positions: int
    follower_id: str
    timestamp: str


@router.post(
    "/manual-close",
    response_model=ManualCloseResponse,
    dependencies=[Depends(get_current_user)],
)
async def manual_close_positions(request: ManualCloseRequest = Body(...)):
    """
    Manually close positions for a specific follower.
    Requires authentication and correct PIN (0312).

    This endpoint triggers the trading bot to close positions for the specified follower.
    """
    # Verify PIN
    settings = get_settings()
    if request.pin != settings.manual_operation_pin:
        logger.warning(
            f"Invalid PIN attempt for manual close: follower_id={request.follower_id}"
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid PIN")

    try:
        db: AsyncIOMotorDatabase = await get_mongo_db()

        # Verify follower exists
        followers_collection = db["followers"]
        follower = await followers_collection.find_one({"_id": request.follower_id})

        if not follower:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Follower {request.follower_id} not found",
            )

        # Initialize IBKR client for the follower
        client = IBKRClient(follower_id=request.follower_id)
        
        try:
            # Call executor.close_all_positions() 
            close_result = await client.close_all_positions()
            
            # Log the manual close request
            logger.info(
                f"Manual close executed for follower {request.follower_id}: {close_result}"
            )
            
            # Create audit trail in database
            manual_operations_collection = db["manual_operations"]
            operation = {
                "type": "MANUAL_CLOSE",
                "follower_id": request.follower_id,
                "close_all": request.close_all,
                "position_ids": request.position_ids,
                "reason": request.reason,
                "status": close_result.get("status", "UNKNOWN"),
                "result": close_result,
                "created_at": datetime.now(pytz.UTC),
                "created_by": "admin_api",
            }
            
            result = await manual_operations_collection.insert_one(operation)
            operation_id = str(result.inserted_id)
            
            # Also create an alert for notification
            alerts_collection = db["alerts"]
            await alerts_collection.insert_one(
                {
                    "type": "MANUAL_CLOSE_EXECUTED",
                    "follower_id": request.follower_id,
                    "operation_id": operation_id,
                    "message": f"Manual close executed for follower {follower.get('name', request.follower_id)}: {close_result.get('status')}",
                    "severity": "HIGH",
                    "timestamp": datetime.now(pytz.UTC),
                    "acknowledged": False,
                }
            )
            
            # Extract closed positions count from result
            closed_positions = close_result.get("closed_positions", 0)
            
            return ManualCloseResponse(
                success=close_result.get("status") == "SUCCESS",
                message=close_result.get("message", f"Operation completed. Operation ID: {operation_id}"),
                closed_positions=closed_positions,
                follower_id=request.follower_id,
                timestamp=datetime.now(pytz.UTC).isoformat(),
            )
            
        except Exception as e:
            logger.error(f"Error executing manual close: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute manual close: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating manual close operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create manual close operation",
        )
