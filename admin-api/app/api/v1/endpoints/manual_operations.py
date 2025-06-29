from datetime import datetime

import os
import pytz
from app.api.v1.endpoints.auth import get_current_user
from fastapi import APIRouter, Body, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from spreadpilot_core.db.mongodb import get_mongo_db
from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# PIN for manual operations - get from environment or Vault
MANUAL_OPERATION_PIN = os.getenv("MANUAL_OPERATION_PIN", "0312")


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
    if request.pin != MANUAL_OPERATION_PIN:
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

        # Create manual close command in the database
        # The trading bot will monitor this collection and execute the closes
        manual_operations_collection = db["manual_operations"]

        operation = {
            "type": "MANUAL_CLOSE",
            "follower_id": request.follower_id,
            "close_all": request.close_all,
            "position_ids": request.position_ids,
            "reason": request.reason,
            "status": "PENDING",
            "created_at": datetime.now(pytz.UTC),
            "created_by": "admin_api",
        }

        result = await manual_operations_collection.insert_one(operation)
        operation_id = str(result.inserted_id)

        # Log the manual close request
        logger.info(
            f"Manual close requested for follower {request.follower_id}, operation_id: {operation_id}"
        )

        # Also create an alert for immediate notification
        alerts_collection = db["alerts"]
        await alerts_collection.insert_one(
            {
                "type": "MANUAL_CLOSE_REQUESTED",
                "follower_id": request.follower_id,
                "operation_id": operation_id,
                "message": f"Manual close requested for follower {follower.get('name', request.follower_id)}",
                "severity": "HIGH",
                "timestamp": datetime.now(pytz.UTC),
                "acknowledged": False,
            }
        )

        # Count current positions that would be affected
        positions_collection = db["positions"]
        if request.close_all:
            position_count = await positions_collection.count_documents(
                {"follower_id": request.follower_id, "status": "OPEN"}
            )
        else:
            position_count = len(request.position_ids) if request.position_ids else 0

        return ManualCloseResponse(
            success=True,
            message=f"Manual close operation created successfully. Operation ID: {operation_id}",
            closed_positions=position_count,
            follower_id=request.follower_id,
            timestamp=datetime.now(pytz.UTC).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating manual close operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create manual close operation",
        )
