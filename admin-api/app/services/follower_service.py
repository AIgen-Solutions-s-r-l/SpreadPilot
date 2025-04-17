from datetime import datetime
from typing import List, Optional
import uuid # For generating unique IDs
import httpx # Import httpx for making HTTP requests

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.models.follower import Follower, FollowerState
from admin_api.app.schemas.follower import FollowerCreate, FollowerRead
from admin_api.app.core.config import get_settings, Settings # Import settings

logger = get_logger(__name__)

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
        Triggers the close positions command for a follower by calling the trading-bot service.
        """
        logger.info(f"Triggering close positions for follower ID: {follower_id}")

        # Construct the target URL using settings
        # Assuming the trading-bot has an endpoint like /api/v1/positions/close
        # This path should ideally also be in settings or a constant
        trading_bot_close_url = f"{self.settings.trading_bot_base_url}/api/v1/positions/close"
        payload = {"follower_id": follower_id}
        
        # Use httpx.AsyncClient for async requests
        async with httpx.AsyncClient(timeout=10.0) as client: # Set a reasonable timeout
            try:
                logger.info(f"Calling trading-bot at {trading_bot_close_url} with payload: {payload}")
                response = await client.post(trading_bot_close_url, json=payload)
                
                # Raise an exception for 4xx or 5xx status codes
                response.raise_for_status()
                
                logger.info(f"Successfully triggered close positions for {follower_id}. Trading-bot response: {response.status_code} - {response.text}")
                
                # Optionally update follower state after successful trigger
                # Consider if this should happen here or be confirmed via another mechanism
                # await self.update_follower_state(follower_id, FollowerState.MANUAL_INTERVENTION)
                
                return True # Indicate success
                
            except httpx.HTTPStatusError as e:
                # Log specific HTTP errors from the trading-bot
                logger.error(f"HTTP error calling trading-bot to close positions for {follower_id}: {e.response.status_code} - {e.response.text}", exc_info=True)
                return False # Indicate failure
            except httpx.RequestError as e:
                # Log network-related errors (connection refused, timeout, etc.)
                logger.error(f"Network error calling trading-bot to close positions for {follower_id}: {e}", exc_info=True)
                return False # Indicate failure
            except Exception as e:
                # Catch any other unexpected errors during the request
                logger.error(f"Unexpected error calling trading-bot to close positions for {follower_id}: {e}", exc_info=True)
                return False # Indicate failure

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