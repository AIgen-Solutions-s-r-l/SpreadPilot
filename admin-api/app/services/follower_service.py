# admin-api/app/services/follower_service.py
from datetime import datetime
from typing import List, Optional
import uuid # For generating unique IDs
import json # For JSON serialization
import importlib

# MongoDB specific imports
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
# from pymongo import ReturnDocument # If using find_one_and_update

from spreadpilot_core.logging.logger import get_logger
# Use the updated Follower model
from spreadpilot_core.models.follower import Follower, FollowerState

# Import modules using importlib
admin_api_schemas = importlib.import_module('admin-api.app.schemas.follower')
admin_api_config = importlib.import_module('admin-api.app.core.config')

# Get specific imports
FollowerCreate = admin_api_schemas.FollowerCreate
FollowerRead = admin_api_schemas.FollowerRead
get_settings = admin_api_config.get_settings
Settings = admin_api_config.Settings

logger = get_logger(__name__)

# Function to publish a message to a topic (remains unchanged)
async def publish_message(topic: str, message_json: str) -> bool:
    """
    Publishes a message to a Pub/Sub topic.
    (Placeholder implementation)
    """
    logger.info(f"Publishing message to topic {topic}: {message_json}")
    try:
        # In a real implementation, this would use the Pub/Sub client
        logger.info(f"Message published successfully to {topic}")
        return True
    except Exception as e:
        logger.error(f"Error publishing message to {topic}: {e}", exc_info=True)
        return False

FOLLOWERS_COLLECTION = "followers" # Collection name remains the same

class FollowerService:
    # Inject AsyncIOMotorDatabase and Settings
    def __init__(self, db: AsyncIOMotorDatabase, settings: Settings):
        self.db = db
        self.settings = settings
        # Get the collection object
        self.collection: AsyncIOMotorCollection = self.db[FOLLOWERS_COLLECTION]

    async def get_followers(self) -> List[FollowerRead]:
        """Retrieves all followers from MongoDB."""
        logger.info("Fetching all followers from MongoDB.")
        followers_read: List[FollowerRead] = []
        try:
            cursor = self.collection.find()
            async for doc in cursor:
                try:
                    # Validate and parse using the Pydantic model
                    # model_validate handles the _id -> id mapping
                    core_follower = Follower.model_validate(doc)
                    # Convert to the API Read schema
                    followers_read.append(FollowerRead(**core_follower.model_dump()))
                except Exception as e:
                    # Log parsing errors for individual documents
                    doc_id = doc.get("_id", "UNKNOWN_ID")
                    logger.error(f"Error parsing follower document {doc_id} from MongoDB: {e}", exc_info=True)
            logger.info(f"Successfully fetched {len(followers_read)} followers from MongoDB.")
            return followers_read
        except Exception as e:
            logger.error(f"Error fetching followers from MongoDB: {e}", exc_info=True)
            raise # Re-raise the exception for the API layer

    async def create_follower(self, follower_create: FollowerCreate) -> FollowerRead:
        """Creates a new follower in MongoDB."""
        logger.info(f"Creating new follower with email: {follower_create.email}")
        try:
            # Generate a unique ID for the new follower (use as _id)
            follower_id = str(uuid.uuid4())

            # Create the core Follower model instance
            now = datetime.utcnow()
            core_follower = Follower(
                id=follower_id, # Pydantic will map this to _id on dump
                created_at=now,
                updated_at=now,
                enabled=False, # Followers start disabled by default
                state=FollowerState.DISABLED,
                **follower_create.model_dump() # Unpack data from the creation schema
            )

            # Convert to dict for MongoDB, mapping id to _id
            # Pydantic's model_dump handles the alias
            follower_data = core_follower.model_dump(by_alias=True)

            # Insert into MongoDB
            insert_result = await self.collection.insert_one(follower_data)

            if insert_result.inserted_id == follower_id:
                logger.info(f"Successfully created follower {follower_id} for {follower_create.email} in MongoDB.")
                # Return the data in the Read schema format
                return FollowerRead(**core_follower.model_dump())
            else:
                # This case should ideally not happen if insert_one doesn't raise an error
                logger.error(f"Failed to insert follower {follower_id} into MongoDB, inserted_id mismatch.")
                raise RuntimeError(f"Failed to create follower {follower_id} in MongoDB.")

        except Exception as e: # Catch potential DuplicateKeyError etc.
            logger.error(f"Error creating follower in MongoDB: {e}", exc_info=True)
            raise

    async def get_follower_by_id(self, follower_id: str) -> Optional[FollowerRead]:
        """Retrieves a single follower by ID (_id) from MongoDB."""
        logger.info(f"Fetching follower with ID: {follower_id} from MongoDB.")
        try:
            # Find by _id
            doc = await self.collection.find_one({"_id": follower_id})

            if doc:
                # Validate and parse
                core_follower = Follower.model_validate(doc)
                logger.info(f"Successfully fetched follower {follower_id} from MongoDB.")
                return FollowerRead(**core_follower.model_dump())
            else:
                logger.warning(f"Follower with ID {follower_id} not found in MongoDB.")
                return None
        except Exception as e:
            logger.error(f"Error fetching follower {follower_id} from MongoDB: {e}", exc_info=True)
            raise

    async def toggle_follower_enabled(self, follower_id: str) -> Optional[FollowerRead]:
        """Toggles the enabled status of a follower in MongoDB."""
        logger.info(f"Toggling enabled status for follower ID: {follower_id} in MongoDB.")
        try:
            # Find the follower first to get current state
            doc = await self.collection.find_one({"_id": follower_id})

            if not doc:
                logger.warning(f"Follower with ID {follower_id} not found for toggling in MongoDB.")
                return None

            current_follower = Follower.model_validate(doc)
            new_enabled = not current_follower.enabled
            new_state = FollowerState.ACTIVE if new_enabled else FollowerState.DISABLED
            now = datetime.utcnow()

            # Update the document
            update_result = await self.collection.update_one(
                {"_id": follower_id},
                {"$set": {
                    "enabled": new_enabled,
                    "state": new_state.value,
                    "updated_at": now
                }}
            )

            if update_result.modified_count == 1:
                logger.info(f"Successfully toggled follower {follower_id} enabled status to {new_enabled} in MongoDB.")
                # Fetch the updated document to return the latest state
                updated_doc = await self.collection.find_one({"_id": follower_id})
                if updated_doc:
                     updated_follower = Follower.model_validate(updated_doc)
                     return FollowerRead(**updated_follower.model_dump())
                else:
                     # Should not happen if update succeeded, but log if it does
                     logger.error(f"Follower {follower_id} disappeared after successful toggle update.")
                     return None # Or raise error
            elif update_result.matched_count == 1 and update_result.modified_count == 0:
                 logger.warning(f"Follower {follower_id} found but status was already {new_enabled}. No change made.")
                 # Return current state
                 return FollowerRead(**current_follower.model_dump())
            else:
                # This case implies the document wasn't found during the update,
                # despite being found initially. Could be a race condition.
                logger.error(f"Failed to toggle follower {follower_id} status. Matched: {update_result.matched_count}, Modified: {update_result.modified_count}")
                return None # Or raise error

        except Exception as e:
            logger.error(f"Error toggling follower {follower_id} status in MongoDB: {e}", exc_info=True)
            raise

    async def trigger_close_positions(self, follower_id: str) -> bool:
        """
        Triggers the close positions command for a follower by publishing a message.
        (No database interaction here, remains unchanged).
        """
        logger.info(f"Triggering close positions for follower ID: {follower_id}")
        try:
            payload = {
                "follower_id": follower_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            message_json = json.dumps(payload)
            result = await publish_message("close-positions", message_json) # Use correct topic name if different

            if result:
                logger.info(f"Successfully triggered close positions for {follower_id}")
                # Optionally update follower state after successful trigger
                # await self.update_follower_state(follower_id, FollowerState.MANUAL_INTERVENTION)
                return True
            else:
                logger.error(f"Failed to trigger close positions for {follower_id} via Pub/Sub.")
                return False
        except Exception as e:
            logger.error(f"Unexpected error triggering close positions for {follower_id}: {e}", exc_info=True)
            return False

    async def update_follower_state(self, follower_id: str, state: FollowerState) -> Optional[FollowerRead]:
        """Updates the state of a follower in MongoDB."""
        logger.info(f"Updating state for follower ID: {follower_id} to {state.value} in MongoDB.")
        try:
            now = datetime.utcnow()
            update_result = await self.collection.update_one(
                {"_id": follower_id},
                {"$set": {
                    "state": state.value,
                    "updated_at": now
                }}
            )

            if update_result.modified_count == 1:
                logger.info(f"Successfully updated follower {follower_id} state to {state.value} in MongoDB.")
                # Fetch the updated document
                updated_doc = await self.collection.find_one({"_id": follower_id})
                if updated_doc:
                    updated_follower = Follower.model_validate(updated_doc)
                    return FollowerRead(**updated_follower.model_dump())
                else:
                    logger.error(f"Follower {follower_id} disappeared after successful state update.")
                    return None
            elif update_result.matched_count == 1 and update_result.modified_count == 0:
                 logger.warning(f"Follower {follower_id} found but state was already {state.value}. No change made.")
                 # Fetch and return current state
                 current_doc = await self.collection.find_one({"_id": follower_id})
                 if current_doc:
                     current_follower = Follower.model_validate(current_doc)
                     return FollowerRead(**current_follower.model_dump())
                 else:
                     logger.error(f"Follower {follower_id} disappeared after no-op state update.")
                     return None
            else:
                logger.error(f"Failed to update follower {follower_id} state. Matched: {update_result.matched_count}, Modified: {update_result.modified_count}")
                return None

        except Exception as e:
            logger.error(f"Error updating follower {follower_id} state in MongoDB: {e}", exc_info=True)
            raise