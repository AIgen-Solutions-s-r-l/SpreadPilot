from fastapi import APIRouter
import importlib

# Import endpoint routers using importlib
admin_api_followers = importlib.import_module('admin_api.app.api.v1.endpoints.followers')
admin_api_dashboard = importlib.import_module('admin_api.app.api.v1.endpoints.dashboard')

# Create the main router for API v1
api_router = APIRouter()

# Include the followers router
api_router.include_router(admin_api_followers.router, tags=["Followers"])
# Include the dashboard WebSocket router
api_router.include_router(admin_api_dashboard.router, tags=["Dashboard"])

# Add other endpoint routers here if needed in the future
# e.g., api_router.include_router(users.router, prefix="/users", tags=["Users"])