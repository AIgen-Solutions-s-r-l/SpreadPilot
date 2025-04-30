import asyncio
import datetime
from typing import List, Set
import importlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
# from google.cloud import firestore # Removed Firestore import
from motor.motor_asyncio import AsyncIOMotorDatabase # Added MongoDB import

from spreadpilot_core.logging.logger import get_logger
from admin_api.app.services.follower_service import FollowerService
from admin_api.app.db.mongodb import get_mongo_db
from admin_api.app.core.config import get_settings

# Dependency to get the follower service
async def get_follower_service() -> FollowerService:
    """
    Dependency to get the follower service.
    """
    db = await get_mongo_db()
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
    # Wrap in try-except to handle errors
    try:
        followers = await follower_service.get_followers()
        
        # Calculate summary statistics
        total_followers = len(followers)
        active_followers = sum(1 for f in followers if f.enabled)
        
        # Return the summary data
        return {
            "follower_count": total_followers,
            "active_follower_count": active_followers,
            "total_positions": 0,  # Placeholder for now
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        # Log the error
        logger.error(f"Error getting dashboard summary: {e}", exc_info=True)
        # Return a 500 error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard summary: {str(e)}"
        )

# Dashboard stats endpoint
@router.get("/dashboard/stats", response_model=dict)
async def get_dashboard_stats(
    follower_service: FollowerService = Depends(get_follower_service)
):
    """
    Get statistics for the dashboard.
    
    Returns:
        dict: A dictionary containing statistics for the dashboard.
    """
    try:
        followers = await follower_service.get_followers()
        
        # Calculate statistics
        total_followers = len(followers)
        active_followers = sum(1 for f in followers if f.enabled)
        
        # Return the statistics
        return {
            "stats": [
                {
                    "type": "followers",
                    "total": total_followers,
                    "active": active_followers,
                    "inactive": total_followers - active_followers
                },
                {
                    "type": "positions",
                    "total": 0,  # Placeholder
                    "profitable": 0,  # Placeholder
                    "losing": 0  # Placeholder
                }
            ],
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard stats: {str(e)}"
        )

# Dashboard alerts endpoint
@router.get("/dashboard/alerts", response_model=dict)
async def get_dashboard_alerts():
    """
    Get alerts for the dashboard.
    
    Returns:
        dict: A dictionary containing alerts for the dashboard.
    """
    try:
        # Placeholder for now
        return {
            "alerts": [],
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard alerts: {str(e)}"
        )

# Dashboard performance endpoint
@router.get("/dashboard/performance", response_model=dict)
async def get_dashboard_performance():
    """
    Get performance data for the dashboard.
    
    Returns:
        dict: A dictionary containing performance data for the dashboard.
    """
    try:
        # Placeholder for now
        return {
            "performance": {
                "daily": 0,
                "weekly": 0,
                "monthly": 0,
                "yearly": 0
            },
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard performance: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard performance: {str(e)}"
        )

# Removed duplicate periodic_follower_update_task function definition.
# The correct definition is above (lines 72-116).


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