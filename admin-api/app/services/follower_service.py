from datetime import datetime

import pymongo
from app.db.mongodb import get_db
from app.schemas.follower import FollowerCreate, FollowerResponse, FollowerUpdate
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)


class FollowerService:
    """Service for managing followers."""

    def __init__(self, db: AsyncIOMotorDatabase = None):
        """Initialize the service with a database connection."""
        self.db = db
        self.collection_name = "followers"

    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the followers collection."""
        if not self.db:
            self.db = await get_db()
        return self.db[self.collection_name]

    async def get_followers(
        self, skip: int = 0, limit: int = 100, status: str | None = None
    ) -> list[FollowerResponse]:
        """Get all followers with optional filtering by status."""
        collection = await self.get_collection()

        # Build query
        query = {}
        if status:
            query["status"] = status

        # Execute query
        cursor = (
            collection.find(query).skip(skip).limit(limit).sort("created_at", pymongo.DESCENDING)
        )

        # Convert to list of FollowerResponse
        followers = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            followers.append(FollowerResponse(**doc))

        return followers

    async def get_follower_count(self) -> int:
        """Get the total number of followers."""
        collection = await self.get_collection()
        return await collection.count_documents({})

    async def get_active_follower_count(self) -> int:
        """Get the number of active followers."""
        collection = await self.get_collection()
        return await collection.count_documents({"status": "active"})

    async def get_follower(self, follower_id: str) -> FollowerResponse | None:
        """Get a follower by ID."""
        collection = await self.get_collection()

        try:
            doc = await collection.find_one({"_id": ObjectId(follower_id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return FollowerResponse(**doc)
            return None
        except Exception as e:
            logger.error(f"Error getting follower {follower_id}: {e}")
            return None

    async def get_follower_by_email(self, email: str) -> FollowerResponse | None:
        """Get a follower by email."""
        collection = await self.get_collection()

        doc = await collection.find_one({"email": email})
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return FollowerResponse(**doc)
        return None

    async def create_follower(self, follower: FollowerCreate) -> FollowerResponse:
        """Create a new follower."""
        collection = await self.get_collection()

        # Prepare document
        now = datetime.utcnow()
        follower_dict = follower.model_dump()
        follower_dict["created_at"] = now
        follower_dict["updated_at"] = now
        follower_dict["preferences"] = {}

        # Insert document
        result = await collection.insert_one(follower_dict)

        # Return created follower
        created_follower = await self.get_follower(str(result.inserted_id))
        return created_follower

    async def update_follower(
        self, follower_id: str, follower_update: FollowerUpdate
    ) -> FollowerResponse | None:
        """Update a follower."""
        collection = await self.get_collection()

        # Prepare update
        update_dict = {k: v for k, v in follower_update.model_dump().items() if v is not None}
        if update_dict:
            update_dict["updated_at"] = datetime.utcnow()

            # Update document
            await collection.update_one({"_id": ObjectId(follower_id)}, {"$set": update_dict})

        # Return updated follower
        return await self.get_follower(follower_id)

    async def delete_follower(self, follower_id: str) -> bool:
        """Delete a follower."""
        collection = await self.get_collection()

        result = await collection.delete_one({"_id": ObjectId(follower_id)})
        return result.deleted_count > 0
