from fastapi import APIRouter
from app.api.v1.endpoints import dashboard, followers, auth, websocket

# Create the main API router
api_router = APIRouter()

# Include the endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(followers.router, prefix="/followers", tags=["Followers"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])