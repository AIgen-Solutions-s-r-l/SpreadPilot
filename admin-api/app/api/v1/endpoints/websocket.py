import json

from app.core.config import get_settings
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


# Store active connections with user context
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, str] = {}  # WebSocket -> username

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username
        logger.info(
            f"WebSocket client connected (user: {username}). Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.pop(websocket, "unknown")
        logger.info(
            f"WebSocket client disconnected (user: {username}). Remaining connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_json(self, data: dict):
        json_data = json.dumps(data)
        await self.broadcast(json_data)


manager = ConnectionManager()


async def validate_ws_token(token: str | None) -> str:
    """Validate JWT token for WebSocket connection.

    Args:
        token: JWT token from query parameter

    Returns:
        Username from token

    Raises:
        Exception with error message if validation fails
    """
    if not token:
        raise Exception("Missing authentication token")

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if not username:
            raise Exception("Invalid token payload")

        # Validate username matches admin (for now, single user system)
        if username != settings.admin_username:
            raise Exception("Unauthorized user")

        logger.info(f"WebSocket token validated for user: {username}")
        return username

    except JWTError as e:
        logger.warning(f"WebSocket JWT validation failed: {e}")
        raise Exception("Invalid or expired token")


# WebSocket endpoint with token authentication
@router.websocket("/dashboard")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """WebSocket endpoint with JWT authentication.

    Args:
        websocket: WebSocket connection
        token: JWT token from query parameter
    """
    try:
        # Validate token before accepting connection
        username = await validate_ws_token(token)

        # Accept connection with authenticated user
        await manager.connect(websocket, username)

        # Connection loop
        while True:
            # Receive and process messages
            data = await websocket.receive_text()

            # Simple echo for now
            await manager.send_personal_message(f"You sent: {data}", websocket)

            # In a real application, you would process the message and potentially
            # broadcast updates to all connected clients

    except Exception as auth_error:
        # Authentication failed - close with 1008 (policy violation)
        logger.warning(f"WebSocket authentication failed: {auth_error}")
        try:
            await websocket.close(code=1008, reason=str(auth_error))
        except:
            pass  # Connection may already be closed

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


# Function to broadcast updates to all connected clients
# This can be called from other parts of the application
async def broadcast_update(data: dict):
    await manager.broadcast_json(data)
