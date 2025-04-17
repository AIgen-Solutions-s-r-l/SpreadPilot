from fastapi import APIRouter

# Import endpoint routers
from admin_api.app.api.v1.endpoints import followers, dashboard

# Create the main router for API v1
api_router = APIRouter()

# Include the followers router
api_router.include_router(followers.router, tags=["Followers"])
# Include the dashboard WebSocket router
api_router.include_router(dashboard.router, tags=["Dashboard"])

# Add other endpoint routers here if needed in the future
# e.g., api_router.include_router(users.router, prefix="/users", tags=["Users"])