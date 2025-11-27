from typing import List, Optional

import pymongo
from app.db.mongodb import get_db
from app.schemas.alert import AlertResponse
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)


class AlertService:
    """Service for managing alerts."""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service."""
        self.db = db
        self.collection_name = "alerts"

    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the alerts collection."""
        if not self.db:
            self.db = await get_db()
        return self.db[self.collection_name]

    async def get_alerts(
        self,
        follower_id: Optional[str] = None,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AlertResponse]:
        """Get alerts with optional filtering."""
        collection = await self.get_collection()

        # Build query
        query = {}
        if follower_id:
            query["follower_id"] = follower_id
        if severity:
            query["severity"] = severity

        # Execute query
        cursor = collection.find(query).sort("timestamp", pymongo.DESCENDING).skip(skip).limit(limit)

        # Convert to response
        alerts = []
        async for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            alerts.append(AlertResponse(**doc))

        return alerts
