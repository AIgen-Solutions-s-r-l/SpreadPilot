from typing import List, Optional

from app.api.v1.endpoints.auth import User, get_current_user
from app.db.mongodb import get_db
from app.schemas.position import PositionResponse
from app.services.position_service import PositionService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[PositionResponse])
async def get_positions(
    follower_id: Optional[str] = Query(None, description="Filter by follower ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get positions with optional filtering.
    """
    try:
        service = PositionService(db=db)
        return await service.get_positions(
            follower_id=follower_id, symbol=symbol, skip=skip, limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting positions: {e!s}",
        )
