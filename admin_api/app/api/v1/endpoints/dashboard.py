import asyncio
import datetime
from typing import List, Set
import importlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
# from google.cloud import firestore # Removed Firestore import
from motor.motor_asyncio import AsyncIOMotorDatabase # Added MongoDB import

from spreadpilot_core.logging.logger import get_logger
from admin_api.app.services.follower_service import FollowerService
from admin_api.app.db.mongodb import get_database
from admin_api.app.core.config import get_settings

# Dependency to get the follower service
async def get_follower_service() -> FollowerService:
    """
    Dependency to get the follower service.
    """
    db = await get_database()
    settings = get_settings()
    return FollowerService(db=db, settings=settings)

# Import modules using importlib
admin_api_db = importlib.import_module('admin_api.app.db.mongodb') # Changed to mongodb
admin_api_services = importlib.import_module('admin_api.app.services.follower_service')
admin_api_schemas = importlib.import_module('admin_api.app.schemas.follower')
admin_api_config = importlib.import_module('admin_api.app.core.config')

# Get specific imports
get_mongo_db = admin_api_db.get_mongo_db # Changed to get_mongo_db
FollowerService = admin_api_services.FollowerService
FollowerRead = admin_api_schemas.FollowerRead
get_settings = admin_api_config.get_settings
Settings = admin_api_config.Settings

logger = get_logger(__name__)

router = APIRouter()

# Keep track of active WebSocket connections
active_connections: Set[WebSocket] = set()

# Function to broadcast updates to all connected WebSocket clients
async def broadcast_updates(message: dict):
    """
    Broadcast a message to all connected WebSocket clients.
    
    Args:
        message: The message to broadcast
    """
    if not active_connections:
        logger.info("No active WebSocket connections to broadcast to")
        return
        
    disconnected_websockets = set()
    
    for websocket in active_connections:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}", exc_info=True)
            disconnected_websockets.add(websocket)
            
    # Remove disconnected WebSockets
    for websocket in disconnected_websockets:
        active_connections.remove(websocket)
        
    logger.info(f"Broadcast message to {len(active_connections)} WebSocket clients")
    
# Periodic task to update followers
async def periodic_follower_update_task(
    follower_service: FollowerService,
    interval_seconds: float = 5.0
):
    """
    Periodic task to fetch follower updates and broadcast them to WebSocket clients.
    
    Args:
        follower_service: The follower service to use
        interval_seconds: The interval between updates in seconds
    """
    logger.info("Starting periodic follower update task for WebSocket.")
    
    while True:
        try:
            # Fetch followers
            followers: List[FollowerRead] = await follower_service.get_followers()
            
            # Prepare the message
            message = {
                "type": "follower_update",
                "data": {
                    "followers": [follower.model_dump() for follower in followers],
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            }
            
            # Broadcast the message
            await broadcast_updates(message)
            
        except Exception as e:
            logger.error(f"Error in periodic follower update task: {e}", exc_info=True)
            
            # Send error message to clients
            error_message = {
                "type": "error",
                "data": {
                    "message": f"Error fetching follower updates: {str(e)}",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            }
            await broadcast_updates(error_message)
            
        # Wait for the next update
        await asyncio.sleep(interval_seconds)
        
# WebSocket endpoint for dashboard updates
@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard updates.
    
    This endpoint:
    1. Accepts WebSocket connections
    2. Adds the connection to the active_connections set
    3. Listens for messages from the client
    4. Removes the connection when the client disconnects
    """
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"New WebSocket connection established. Total connections: {len(active_connections)}")
    
    try:
        # Send initial data
        follower_service = FollowerService(
            db=await get_database(),
            settings=get_settings()
        )
        
        followers = await follower_service.get_followers()
        initial_message = {
            "type": "initial_data",
            "data": {
                "followers": [follower.model_dump() for follower in followers],
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }
        await websocket.send_json(initial_message)
        
        # Listen for messages from the client
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from WebSocket client: {data}")
            
            # Process client messages if needed
            # For now, just echo back
            await websocket.send_json({
                "type": "echo",
                "data": data
            })
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Remaining connections: {len(active_connections)}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}", exc_info=True)
        if websocket in active_connections:
            active_connections.remove(websocket)

# Dashboard API endpoints
@router.get("/dashboard/summary", response_model=dict)
async def get_dashboard_summary(
    follower_service: FollowerService = Depends(get_follower_service)
):
    """
    Get a summary of the dashboard data.
    
    Returns:
        dict: A dictionary containing summary data for the dashboard.
    """
    try:
        followers = await follower_service.get_followers()
        
        # Calculate summary statistics
        total_followers = len(followers)
        active_followers = sum(1 for f in followers if f.enabled)
        
        # Return the summary data
        return {
            "total_followers": total_followers,
            "active_followers": active_followers,
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard summary: {str(e)}"
        )

# Dependency to get the FollowerService instance (using MongoDB)
def get_follower_service(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db), # Changed dependency and type hint
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
    
    # Create follower_service if not provided (e.g., when run standalone, though usually started via lifespan)
    if follower_service is None:
        # Use the already imported modules for MongoDB
        # Note: This relies on the global client being initialized elsewhere,
        # which might be fragile if this task runs truly independently.
        # Ideally, the service instance is always passed from the lifespan manager.
        try:
            db = await get_mongo_db() # Get the MongoDB instance
            settings = get_settings()
            follower_service = FollowerService(db=db, settings=settings)
            logger.info("Created follower service for periodic task using MongoDB")
        except Exception as e:
            logger.error(f"Failed to create FollowerService in periodic task: {e}", exc_info=True)
            # Exit the task if service cannot be created
            return

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
        await websocket.close() # Explicitly close on initial state error

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