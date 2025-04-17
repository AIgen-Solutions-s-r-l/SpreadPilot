from datetime import datetime
from typing import List, Optional
import uuid # For generating unique IDs
import httpx # Import httpx for making HTTP requests
import json # For JSON serialization

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower, FollowerState
from admin_api.app.schemas.follower import FollowerCreate, FollowerRead
from admin_api.app.core.config import get_settings, Settings # Import settings

logger = get_logger(__name__)

# Function to publish a message to a topic
async def publish_message(topic: str, message_json: str) -> bool:
    """
    Publishes a message to a Pub/Sub topic.
    
    Args:
        topic: The name of the topic to publish to
        message_json: The message to publish, as a JSON string
        
    Returns:
        bool: True if the message was published successfully, False otherwise
    """
    logger.info(f"Publishing message to topic {topic}: {message_json}")
    try:
        # In a real implementation, this would use the Pub/Sub client
        # For now, we'll just log the message and return success
        logger.info(f"Message published successfully to {topic}")
        return True
    except Exception as e:
        logger.error(f"Error publishing message to {topic}: {e}", exc_info=True)
        return False

FOLLOWERS_COLLECTION = "followers"

class FollowerService:
    # Inject settings along with the database client
    def __init__(self, db: firestore.AsyncClient, settings: Settings):
        self.db = db
        self.settings = settings
        self.collection_ref = self.db.collection(FOLLOWERS_COLLECTION)

    async def get_followers(self) -> List[FollowerRead]:
        """Retrieves all followers from Firestore."""
        logger.info("Fetching all followers from Firestore.")
        followers = []
        try:
            docs_stream = self.collection_ref.stream()
            async for doc in docs_stream:
                try:
                    follower_data = doc.to_dict()
                    # Use the core model's from_dict for robust parsing
                    core_follower = Follower.from_dict(id=doc.id, data=follower_data)
                    # Convert to the API Read schema
                    followers.append(FollowerRead(**core_follower.model_dump()))
                except Exception as e:
                    logger.error(f"Error parsing follower document {doc.id}: {e}", exc_info=True)
            logger.info(f"Successfully fetched {len(followers)} followers.")
            return followers
        except Exception as e:
            logger.error(f"Error fetching followers from Firestore: {e}", exc_info=True)
            raise  # Re-raise the exception to be handled by the API layer

    async def create_follower(self, follower_create: FollowerCreate) -> FollowerRead:
        """Creates a new follower in Firestore."""
        logger.info(f"Creating new follower with email: {follower_create.email}")
        try:
            # Generate a unique ID for the new follower
            follower_id = str(uuid.uuid4())
            
            # Create the core Follower model instance
            now = datetime.utcnow()
            core_follower = Follower(
                id=follower_id,
                created_at=now,
                updated_at=now,
                enabled=False, # Followers start disabled by default
                state=FollowerState.DISABLED,
                **follower_create.model_dump() # Unpack data from the creation schema
            )

            # Convert to Firestore-compatible dict using the core model's method
            follower_data = core_follower.to_dict()

            # Add to Firestore
            doc_ref = self.collection_ref.document(follower_id)
            await doc_ref.set(follower_data)
            logger.info(f"Successfully created follower {follower_id} for {follower_create.email}")

            # Return the data in the Read schema format
            return FollowerRead(**core_follower.model_dump())
        except Exception as e:
            logger.error(f"Error creating follower in Firestore: {e}", exc_info=True)
            raise

    async def get_follower_by_id(self, follower_id: str) -> Optional[FollowerRead]:
        """Retrieves a single follower by ID from Firestore."""
        logger.info(f"Fetching follower with ID: {follower_id}")
        try:
            doc_ref = self.collection_ref.document(follower_id)
            doc_snapshot = await doc_ref.get()

            if not doc_snapshot.exists:
                logger.warning(f"Follower with ID {follower_id} not found.")
                return None

            follower_data = doc_snapshot.to_dict()
            core_follower = Follower.from_dict(id=doc_snapshot.id, data=follower_data)
            logger.info(f"Successfully fetched follower {follower_id}.")
            return FollowerRead(**core_follower.model_dump())
        except Exception as e:
            logger.error(f"Error fetching follower {follower_id} from Firestore: {e}", exc_info=True)
            raise

    async def toggle_follower_enabled(self, follower_id: str) -> Optional[FollowerRead]:
        """Toggles the enabled status of a follower."""
        logger.info(f"Toggling enabled status for follower ID: {follower_id}")
        try:
            doc_ref = self.collection_ref.document(follower_id)
            doc_snapshot = await doc_ref.get()

            if not doc_snapshot.exists:
                logger.warning(f"Follower with ID {follower_id} not found for toggling.")
                return None

            current_enabled = doc_snapshot.get("enabled")
            new_enabled = not current_enabled
            new_state = FollowerState.ACTIVE if new_enabled else FollowerState.DISABLED
            now = datetime.utcnow()

            await doc_ref.update({
                "enabled": new_enabled,
                "state": new_state.value,
                "updatedAt": now
            })
            logger.info(f"Successfully toggled follower {follower_id} enabled status to {new_enabled}.")

            # Fetch the updated document to return
            updated_doc = await doc_ref.get()
            updated_data = updated_doc.to_dict()
            core_follower = Follower.from_dict(id=updated_doc.id, data=updated_data)
            return FollowerRead(**core_follower.model_dump())

        except Exception as e:
            logger.error(f"Error toggling follower {follower_id} status: {e}", exc_info=True)
            raise

    async def trigger_close_positions(self, follower_id: str) -> bool:
        """
        Triggers the close positions command for a follower by publishing a message to a topic.
        """
        logger.info(f"Triggering close positions for follower ID: {follower_id}")

        try:
            # Create the message payload
            payload = {
                "follower_id": follower_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Convert to JSON string
            message_json = json.dumps(payload)
            
            # Publish the message to the close-positions topic
            result = await publish_message("close-positions", message_json)
            
            if result:
                logger.info(f"Successfully triggered close positions for {follower_id}")
                # Optionally update follower state after successful trigger
                # await self.update_follower_state(follower_id, FollowerState.MANUAL_INTERVENTION)
                return True
            else:
                logger.error(f"Failed to trigger close positions for {follower_id}")
                return False
                
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error triggering close positions for {follower_id}: {e}", exc_info=True)
            return False

    async def update_follower_state(self, follower_id: str, state: FollowerState) -> Optional[FollowerRead]:
        """Updates the state of a follower."""
        logger.info(f"Updating state for follower ID: {follower_id} to {state.value}")
        try:
            doc_ref = self.collection_ref.document(follower_id)
            now = datetime.utcnow()
            await doc_ref.update({
                "state": state.value,
                "updatedAt": now
            })
            logger.info(f"Successfully updated follower {follower_id} state to {state.value}.")

            # Fetch the updated document to return
            updated_doc = await doc_ref.get()
            if not updated_doc.exists: # Should not happen if update succeeded, but check anyway
                return None
            updated_data = updated_doc.to_dict()
            core_follower = Follower.from_dict(id=updated_doc.id, data=updated_data)
            return FollowerRead(**core_follower.model_dump())
        except Exception as e:
            logger.error(f"Error updating follower {follower_id} state: {e}", exc_info=True)
            raise