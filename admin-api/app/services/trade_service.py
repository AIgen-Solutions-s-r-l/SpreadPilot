from typing import List, Optional

import pymongo
from app.db.mongodb import get_db
from app.schemas.trade import TradeResponse
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)


class TradeService:
    """Service for managing trades."""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service."""
        self.db = db
        self.collection_name = "trades"

    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the trades collection."""
        if not self.db:
            self.db = await get_db()
        return self.db[self.collection_name]

    async def get_trades(
        self,
        follower_id: Optional[str] = None,
        symbol: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TradeResponse]:
        """Get trades with optional filtering."""
        collection = await self.get_collection()

        # Build query
        query = {}
        if follower_id:
            query["follower_id"] = follower_id
        if symbol:
            query["symbol"] = symbol

        # Execute query - sort by submission time usually
        # The CoreTrade model has 'timestamps.submitted', so we can sort by that if indexed
        # Or just natural order/insertion time
        cursor = collection.find(query).sort("_id", pymongo.DESCENDING).skip(skip).limit(limit)

        # Convert to response
        trades = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            trades.append(TradeResponse(**doc))

        return trades
