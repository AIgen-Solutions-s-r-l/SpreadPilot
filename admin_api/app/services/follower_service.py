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
admin_api_schemas = importlib.import_module('admin_api.app.schemas.follower')
admin_api_config = importlib.import_module('admin_api.app.core.config')

# Get specific imports
FollowerCreate = admin_api_schemas.FollowerCreate
FollowerRead = admin_api_schemas.FollowerRead
FollowerUpdate = admin_api_schemas.FollowerUpdate
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
            # Check if follower with this email already exists
            existing_follower = await self.get_follower_by_email(follower_create.email)
            if existing_follower:
                logger.warning(f"Attempted to create follower with duplicate email: {follower_create.email}")
                # Raise a specific exception or return an indicator? For API, raise HTTPExc.
                # For now, let's raise a ValueError that the endpoint can catch.
                raise ValueError(f"Follower with email {follower_create.email} already exists.")

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

        except ValueError as ve: # Catch specific duplicate error
             logger.error(f"Error creating follower: {ve}")
             raise # Re-raise for the endpoint to handle (e.g., return 400)
        except Exception as e: # Catch other potential errors
            logger.error(f"Error creating follower in MongoDB: {e}", exc_info=True)
            raise

    async def get_follower_by_id(self, follower_id: str) -> Optional[FollowerRead]:
        """Retrieves a single follower by ID (_id) from MongoDB."""
        logger.info(f"Fetching follower with ID: {follower_id} from MongoDB.")
        try:
            # Find by _id using the provided string ID (assuming _id is stored as string)
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
            
    async def get_follower_by_email(self, email: str) -> Optional[FollowerRead]:
        """Retrieves a single follower by email from MongoDB."""
        logger.info(f"Fetching follower with email: {email} from MongoDB.")
        try:
            # Find by email
            doc = await self.collection.find_one({"email": email})
            
            if doc:
                # Validate and parse
                core_follower = Follower.model_validate(doc)
                logger.info(f"Successfully fetched follower with email {email} from MongoDB.")
                return FollowerRead(**core_follower.model_dump())
            else:
                logger.warning(f"Follower with email {email} not found in MongoDB.")
                return None
        except Exception as e:
            logger.error(f"Error fetching follower with email {email} from MongoDB: {e}", exc_info=True)
            raise

    async def toggle_follower_enabled(self, follower_id: str) -> Optional[FollowerRead]:
        """Toggles the enabled status of a follower in MongoDB."""
        logger.info(f"Toggling enabled status for follower ID: {follower_id} in MongoDB.")
        try:
            # Find the follower first to get current state using string ID
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
                {"_id": follower_id}, # Use string ID for update filter
                {"$set": {
                    "enabled": new_enabled,
                    "state": new_state.value,
                    "updated_at": now
                }}
            )

            if update_result.modified_count == 1:
                logger.info(f"Successfully toggled follower {follower_id} enabled status to {new_enabled} in MongoDB.")
                # Fetch the updated document to return the latest state
                updated_doc = await self.collection.find_one({"_id": follower_id}) # Use string ID
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
            # Use string ID for update filter
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
                updated_doc = await self.collection.find_one({"_id": follower_id}) # Use string ID
                if updated_doc:
                    updated_follower = Follower.model_validate(updated_doc)
                    return FollowerRead(**updated_follower.model_dump())
                else:
                    logger.error(f"Follower {follower_id} disappeared after successful state update.")
                    return None
            elif update_result.matched_count == 1 and update_result.modified_count == 0:
                 logger.warning(f"Follower {follower_id} found but state was already {state.value}. No change made.")
                 # Fetch and return current state
                 current_doc = await self.collection.find_one({"_id": follower_id}) # Use string ID
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
    
    async def update_follower(self, follower_id: str, follower_update: FollowerUpdate) -> Optional[FollowerRead]:
        """Updates a follower in MongoDB."""
        logger.info(f"Updating follower with ID: {follower_id} in MongoDB.")
        try:
            # Get the current follower
            current_doc = await self.collection.find_one({"_id": follower_id})
            if not current_doc:
                logger.warning(f"Follower with ID {follower_id} not found for update in MongoDB.")
                return None
                
            # Create update dict with only non-None fields
            update_data = {k: v for k, v in follower_update.model_dump().items() if v is not None}
            
            # Add updated_at timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            # Update the document
            update_result = await self.collection.update_one(
                {"_id": follower_id},
                {"$set": update_data}
            )
            
            if update_result.modified_count == 1:
                logger.info(f"Successfully updated follower {follower_id} in MongoDB.")
                # Fetch the updated document
                updated_doc = await self.collection.find_one({"_id": follower_id})
                if updated_doc:
                    updated_follower = Follower.model_validate(updated_doc)
                    return FollowerRead(**updated_follower.model_dump())
                else:
                    logger.error(f"Follower {follower_id} disappeared after successful update.")
                    return None
            elif update_result.matched_count == 1 and update_result.modified_count == 0:
                logger.warning(f"Follower {follower_id} found but no changes were made. No update needed.")
                # Return current state
                current_follower = Follower.model_validate(current_doc)
                return FollowerRead(**current_follower.model_dump())
            else:
                logger.error(f"Failed to update follower {follower_id}. Matched: {update_result.matched_count}, Modified: {update_result.modified_count}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating follower {follower_id} in MongoDB: {e}", exc_info=True)
            raise
    
    async def delete_follower(self, follower_id: str) -> bool:
        """Deletes a follower from MongoDB."""
        logger.info(f"Deleting follower with ID: {follower_id} from MongoDB.")
        try:
            # Delete the document
            delete_result = await self.collection.delete_one({"_id": follower_id})
            
            if delete_result.deleted_count == 1:
                logger.info(f"Successfully deleted follower {follower_id} from MongoDB.")
                return True
            else:
                logger.warning(f"Follower with ID {follower_id} not found for deletion in MongoDB.")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting follower {follower_id} from MongoDB: {e}", exc_info=True)
            raise
            
    async def _record_trade_in_db(self, follower_id: str, trade_data: dict) -> bool:
        """
        Records a trade in the database for a specific follower.
        
        Args:
            follower_id: The ID of the follower
            trade_data: Dictionary containing trade details
            
        Returns:
            bool: True if the trade was successfully recorded, False otherwise
        """
        logger.info(f"Recording trade for follower ID: {follower_id} in MongoDB")
        try:
            # Create a trades collection if it doesn't exist
            trades_collection = self.db["follower_trades"]
            
            # Add metadata to the trade
            trade_record = {
                **trade_data,
                "follower_id": follower_id,
                "recorded_at": datetime.utcnow(),
                "trade_id": str(uuid.uuid4())
            }
            
            # Insert the trade record
            result = await trades_collection.insert_one(trade_record)
            
            if result.inserted_id:
                logger.info(f"Successfully recorded trade {trade_record['trade_id']} for follower {follower_id}")
                return True
            else:
                logger.error(f"Failed to record trade for follower {follower_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error recording trade for follower {follower_id}: {e}", exc_info=True)
            return False
            
    async def get_follower_trades(self, follower_id: str, limit: int = 100) -> List[dict]:
        """
        Retrieves the most recent trades for a follower.
        
        Args:
            follower_id: The ID of the follower
            limit: Maximum number of trades to return
            
        Returns:
            List[dict]: List of trade records
        """
        logger.info(f"Fetching trades for follower ID: {follower_id} from MongoDB")
        try:
            trades_collection = self.db["follower_trades"]
            
            # Query trades for this follower, sorted by timestamp descending
            cursor = trades_collection.find(
                {"follower_id": follower_id}
            ).sort("recorded_at", -1).limit(limit)
            
            trades = []
            async for trade in cursor:
                # Convert ObjectId to string for JSON serialization
                if "_id" in trade:
                    trade["_id"] = str(trade["_id"])
                trades.append(trade)
                
            logger.info(f"Successfully fetched {len(trades)} trades for follower {follower_id}")
            return trades
            
        except Exception as e:
            logger.error(f"Error fetching trades for follower {follower_id}: {e}", exc_info=True)
            return []
            
    async def _get_trades_from_db(self, follower_id: str, limit: int = 100) -> List[dict]:
        """
        Internal method to retrieve trades from the database.
        This is the actual implementation of get_follower_trades.
        
        Args:
            follower_id: The ID of the follower
            limit: Maximum number of trades to return
            
        Returns:
            List[dict]: List of trade records
        """
        # This method is implemented by get_follower_trades
        # We're adding this as a separate method to match the test's expectations
        return await self.get_follower_trades(follower_id, limit)
    
    async def _get_positions_from_db(self, follower_id: str, limit: int = 100) -> List[dict]:
        """
        Internal method to retrieve positions from the database.
        This is the actual implementation of get_follower_positions.
        
        Args:
            follower_id: The ID of the follower
            limit: Maximum number of positions to return
            
        Returns:
            List[dict]: List of position records
        """
        # This method is implemented by get_follower_positions
        # We're adding this as a separate method to match the test's expectations
        return await self.get_follower_positions(follower_id, limit)
            
    async def get_followers_by_ids(self, follower_ids: List[str]) -> List[FollowerRead]:
        """
        Retrieves multiple followers by their IDs.
        
        Args:
            follower_ids: List of follower IDs to retrieve
            
        Returns:
            List[FollowerRead]: List of retrieved followers
        """
        logger.info(f"Fetching {len(follower_ids)} followers by IDs from MongoDB")
        followers = []
        
        try:
            # Use $in operator to fetch multiple documents at once
            cursor = self.collection.find({"_id": {"$in": follower_ids}})
            
            async for doc in cursor:
                try:
                    core_follower = Follower.model_validate(doc)
                    followers.append(FollowerRead(**core_follower.model_dump()))
                except Exception as e:
                    doc_id = doc.get("_id", "UNKNOWN_ID")
                    logger.error(f"Error parsing follower document {doc_id} from MongoDB: {e}", exc_info=True)
            
            logger.info(f"Successfully fetched {len(followers)} followers by IDs from MongoDB")
            return followers
            
        except Exception as e:
            logger.error(f"Error fetching followers by IDs from MongoDB: {e}", exc_info=True)
            raise
            
    async def record_trade(self, trade_data: dict) -> bool:
        """
        Records a trade for a follower.
        
        Args:
            trade_data: Dictionary containing trade details
            
        Returns:
            bool: True if the trade was successfully recorded, False otherwise
        """
        follower_id = trade_data.get("follower_id")
        if not follower_id:
            logger.error("Cannot record trade: missing follower_id in trade data")
            return False
            
        logger.info(f"Recording trade for follower ID: {follower_id}")
        
        try:
            # Use the internal method to record the trade
            result = await self._record_trade_in_db(follower_id, trade_data)
            return result
        except Exception as e:
            logger.error(f"Error recording trade for follower {follower_id}: {e}", exc_info=True)
            return False
            
    async def create_followers_batch(self, followers_create: List[FollowerCreate]) -> List[FollowerRead]:
        """
        Creates multiple followers in a batch operation.
        
        Args:
            followers_create: List of FollowerCreate objects
            
        Returns:
            List[FollowerRead]: List of created followers
        """
        logger.info(f"Creating batch of {len(followers_create)} followers in MongoDB")
        created_followers = []
        
        try:
            # Process each follower creation
            for follower_create in followers_create:
                try:
                    created_follower = await self.create_follower(follower_create)
                    if created_follower:
                        created_followers.append(created_follower)
                except Exception as e:
                    logger.error(f"Error creating follower {follower_create.email} in batch: {e}", exc_info=True)
                    # Continue with the next follower
            
            logger.info(f"Successfully created {len(created_followers)} followers in batch operation")
            return created_followers
            
        except Exception as e:
            logger.error(f"Error in batch follower creation: {e}", exc_info=True)
            raise
            
    async def update_followers_batch(self, updates: List[tuple[str, FollowerUpdate]]) -> List[FollowerRead]:
        """
        Updates multiple followers in a batch operation.
        
        Args:
            updates: List of tuples containing (follower_id, FollowerUpdate)
            
        Returns:
            List[FollowerRead]: List of updated followers
        """
        logger.info(f"Updating batch of {len(updates)} followers in MongoDB")
        updated_followers = []
        
        try:
            # Process each follower update
            for follower_id, follower_update in updates:
                try:
                    updated_follower = await self.update_follower(follower_id, follower_update)
                    if updated_follower:
                        updated_followers.append(updated_follower)
                except Exception as e:
                    logger.error(f"Error updating follower {follower_id} in batch: {e}", exc_info=True)
                    # Continue with the next follower
            
            logger.info(f"Successfully updated {len(updated_followers)} followers in batch operation")
            return updated_followers
            
        except Exception as e:
            logger.error(f"Error in batch follower update: {e}", exc_info=True)
            raise
            
    async def delete_followers_batch(self, follower_ids: List[str]) -> int:
        """
        Deletes multiple followers in a batch operation.
        
        Args:
            follower_ids: List of follower IDs to delete
            
        Returns:
            int: Number of followers successfully deleted
        """
        logger.info(f"Deleting batch of {len(follower_ids)} followers from MongoDB")
        deleted_count = 0
        
        try:
            # Process each follower deletion
            for follower_id in follower_ids:
                try:
                    success = await self.delete_follower(follower_id)
                    if success:
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting follower {follower_id} in batch: {e}", exc_info=True)
                    # Continue with the next follower
            
            logger.info(f"Successfully deleted {deleted_count} followers in batch operation")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error in batch follower deletion: {e}", exc_info=True)
            raise
            
    async def get_follower_positions(self, follower_id: str, limit: int = 100) -> List[dict]:
        """
        Retrieves the current positions for a follower.
        
        Args:
            follower_id: The ID of the follower
            limit: Maximum number of positions to return
            
        Returns:
            List[dict]: List of position records
        """
        logger.info(f"Fetching positions for follower ID: {follower_id} from MongoDB")
        try:
            positions_collection = self.db["follower_positions"]
            
            # Query positions for this follower
            cursor = positions_collection.find(
                {"follower_id": follower_id}
            ).limit(limit)
            
            positions = []
            async for position in cursor:
                # Convert ObjectId to string for JSON serialization
                if "_id" in position:
                    position["_id"] = str(position["_id"])
                positions.append(position)
                
            logger.info(f"Successfully fetched {len(positions)} positions for follower {follower_id}")
            return positions
            
        except Exception as e:
            logger.error(f"Error fetching positions for follower {follower_id}: {e}", exc_info=True)
            return []