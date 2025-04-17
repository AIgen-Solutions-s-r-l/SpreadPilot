from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin_api.app.api.v1.api import api_router
from admin_api.app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="SpreadPilot Admin API",
    description="Admin API for SpreadPilot trading system",
    version="0.1.0",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to SpreadPilot Admin API"}

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}