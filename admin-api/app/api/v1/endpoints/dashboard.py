import asyncio
from typing import List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from google.cloud import firestore

from spreadpilot_core.logging.logger import get_logger
from admin_api.app.db.firestore import get_db
from admin_api.app.services.follower_service import FollowerService
from admin_api.app.schemas.follower import FollowerRead
from admin_api.app.core.config import get_settings, Settings

logger = get_logger(__name__)

router = APIRouter()

# Keep track of active WebSocket connections
active_connections: Set[WebSocket] = set()

# Dependency to get the FollowerService instance (same as in followers.py)
def get_follower_service(
    db: firestore.AsyncClient = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> FollowerService:
    return FollowerService(db=db, settings=settings)


async def broadcast_updates(message: dict):
    """Sends a message to all active WebSocket connections."""
    disconnected_connections = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except WebSocketDisconnect:
            logger.info("Client disconnected during broadcast.")
            disconnected_connections.add(connection)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}", exc_info=True)
            disconnected_connections.add(connection)
    
    # Remove disconnected clients
    for conn in disconnected_connections:
        if conn in active_connections:
            active_connections.remove(conn)


async def periodic_follower_update_task(follower_service: FollowerService = None, interval_seconds: int = 15):
    """Periodically fetches follower data and broadcasts updates."""
    logger.info("Starting periodic follower update task for WebSocket.")
    
    # Create follower_service if not provided
    if follower_service is None:
        from admin_api.app.db.firestore import get_firestore_client
        from admin_api.app.core.config import get_settings
        db = get_firestore_client()
        settings = get_settings()
        follower_service = FollowerService(db=db, settings=settings)
        logger.info("Created follower service for periodic task")
    
    while True:
        try:
            followers: List[FollowerRead] = await follower_service.get_followers()
            # Convert Pydantic models to dicts for JSON serialization
            followers_data = [f.model_dump(mode='json') for f in followers]
            update_message = {"type": "followers_update", "data": followers_data}
            if active_connections: # Only broadcast if there are active connections
                logger.debug(f"Broadcasting follower updates to {len(active_connections)} clients.")
                await broadcast_updates(update_message)
            else:
                logger.debug("No active WebSocket connections, skipping broadcast.")
        except Exception as e:
            logger.error(f"Error in periodic follower update task: {e}", exc_info=True)
        
        # Wait for the next interval
        await asyncio.sleep(interval_seconds)


@router.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(
    websocket: WebSocket,
    follower_service: FollowerService = Depends(get_follower_service)
):
    """
    WebSocket endpoint for real-time dashboard updates.

    Sends periodic updates of follower status.
    """
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"WebSocket client connected: {websocket.client}. Total clients: {len(active_connections)}")
    
    # Send initial data immediately upon connection
    try:
        initial_followers = await follower_service.get_followers()
        initial_data = [f.model_dump(mode='json') for f in initial_followers]
        await websocket.send_json({"type": "initial_state", "data": {"followers": initial_data}})
        logger.info(f"Sent initial state to client: {websocket.client}")
    except Exception as e:
        logger.error(f"Error sending initial state to {websocket.client}: {e}", exc_info=True)

    try:
        while True:
            # Keep the connection alive, listen for messages (optional)
            # For now, this loop just keeps the connection open.
            # We could add handling for client messages if needed.
            data = await websocket.receive_text() 
            # Example: Handle client messages if necessary
            # logger.debug(f"Received message from {websocket.client}: {data}")
            # await websocket.send_text(f"Message received: {data}") 
            await asyncio.sleep(0.1) # Prevent tight loop if receive_text returns immediately
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"WebSocket error for client {websocket.client}: {e}", exc_info=True)
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"WebSocket connection closed for: {websocket.client}. Total clients: {len(active_connections)}")

# How to start the background task?
# We need a lifespan manager in main.py to start/stop the periodic task.