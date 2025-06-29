from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    dashboard,
    followers,
    health,
    logs,
    manual_operations,
    pnl,
    websocket,
)

# Create the main API router
api_router = APIRouter()

# Include the endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(followers.router, prefix="/followers", tags=["Followers"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(pnl.router, prefix="/pnl", tags=["P&L"])
api_router.include_router(logs.router, prefix="/logs", tags=["Logs"])
api_router.include_router(manual_operations.router, tags=["Manual Operations"])
api_router.include_router(health.router, tags=["Health"])
