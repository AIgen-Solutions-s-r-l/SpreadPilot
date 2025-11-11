"""MongoDB client for paper trading gateway."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from ..config import get_settings


class MongoDBClient:
    """MongoDB client wrapper."""

    def __init__(self):
        """Initialize MongoDB client."""
        self.settings = get_settings()
        self.client: AsyncIOMotorClient = None
        self.db: AsyncIOMotorDatabase = None

    async def connect(self):
        """Connect to MongoDB."""
        if self.client is None:
            self.client = AsyncIOMotorClient(self.settings.mongo_uri)
            self.db = self.client[self.settings.mongo_db_name]

            # Create indexes
            await self._create_indexes()

    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None

    async def _create_indexes(self):
        """Create database indexes."""
        # Orders indexes
        await self.db.orders.create_index([("order_id", ASCENDING)], unique=True)
        await self.db.orders.create_index([("symbol", ASCENDING)])
        await self.db.orders.create_index([("timestamp", DESCENDING)])
        await self.db.orders.create_index([("status", ASCENDING)])

        # Positions indexes
        await self.db.positions.create_index([("symbol", ASCENDING)], unique=True)

        # Account indexes (only one account for paper trading)
        await self.db.account.create_index([("created_at", DESCENDING)])

    def get_orders_collection(self):
        """Get orders collection."""
        return self.db.orders

    def get_positions_collection(self):
        """Get positions collection."""
        return self.db.positions

    def get_account_collection(self):
        """Get account collection."""
        return self.db.account


# Singleton instance
_mongo_client = None


def get_mongo_client() -> MongoDBClient:
    """Get MongoDB client singleton."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoDBClient()
    return _mongo_client
