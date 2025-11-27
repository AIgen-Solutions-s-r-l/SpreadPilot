from typing import List, Optional

from app.api.v1.endpoints.auth import User, get_current_user
from app.db.mongodb import get_db
from app.schemas.trade import TradeResponse
from app.services.trade_service import TradeService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[TradeResponse])
async def get_trades(
    follower_id: Optional[str] = Query(None, description="Filter by follower ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get trades with optional filtering.
    """
    try:
        service = TradeService(db=db)
        return await service.get_trades(
            follower_id=follower_id, symbol=symbol, skip=skip, limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trades: {e!s}",
        )
