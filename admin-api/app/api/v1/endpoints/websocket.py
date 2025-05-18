from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from app.api.v1.endpoints.auth import get_current_user, User
from app.core.config import get_settings
from spreadpilot_core.logging.logger import get_logger
import json
from typing import List, Dict

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_json(self, data: dict):
        json_data = json.dumps(data)
        await self.broadcast(json_data)

manager = ConnectionManager()

# WebSocket endpoint with token authentication
@router.websocket("/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive and process messages
            data = await websocket.receive_text()
            
            # Simple echo for now
            await manager.send_personal_message(f"You sent: {data}", websocket)
            
            # In a real application, you would process the message and potentially
            # broadcast updates to all connected clients
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Function to broadcast updates to all connected clients
# This can be called from other parts of the application
async def broadcast_update(data: dict):
    await manager.broadcast_json(data)