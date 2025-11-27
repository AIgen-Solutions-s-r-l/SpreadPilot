from typing import List, Optional

import pymongo
from app.db.mongodb import get_db
from app.schemas.position import PositionResponse
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)


class PositionService:
    """Service for managing positions."""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service."""
        self.db = db
        self.collection_name = "positions"

    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the positions collection."""
        if not self.db:
            self.db = await get_db()
        return self.db[self.collection_name]

    async def get_positions(
        self,
        follower_id: Optional[str] = None,
        symbol: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PositionResponse]:
        """Get positions with optional filtering."""
        collection = await self.get_collection()

        # Build query
        query = {}
        if follower_id:
            query["follower_id"] = follower_id
        if symbol:
            query["symbol"] = symbol

        # Execute query
        cursor = collection.find(query).skip(skip).limit(limit)

        # Convert to response
        positions = []
        async for doc in cursor:
            # Handle ObjectId if present, though Position model usually uses str id
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            positions.append(PositionResponse(**doc))

        return positions
