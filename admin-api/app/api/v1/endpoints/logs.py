from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from typing import List, Optional
from app.api.v1.endpoints.auth import get_current_user, User
from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.db.mongodb import get_mongo_db
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()
logger = get_logger(__name__)


@router.get("/recent", dependencies=[Depends(get_current_user)])
async def get_recent_logs(
    n: int = Query(default=200, ge=1, le=1000, description="Number of log entries to retrieve"),
    service: Optional[str] = Query(default=None, description="Filter by service name"),
    level: Optional[str] = Query(default=None, description="Filter by log level (INFO, WARNING, ERROR)"),
    search: Optional[str] = Query(default=None, description="Search text in log messages")
):
    """
    Get recent log entries from all services.
    
    Parameters:
    - n: Number of log entries to retrieve (1-1000, default: 200)
    - service: Optional filter by service name
    - level: Optional filter by log level
    - search: Optional text search in log messages
    """
    try:
        db: AsyncIOMotorDatabase = await get_mongo_db()
        logs_collection = db["logs"]
        
        # Build query filter
        query_filter = {}
        
        if service:
            query_filter["service"] = service
            
        if level:
            query_filter["level"] = level.upper()
            
        if search:
            # Case-insensitive search in message field
            query_filter["message"] = {"$regex": search, "$options": "i"}
        
        # Query logs, sorted by timestamp descending
        cursor = logs_collection.find(
            query_filter,
            {
                "_id": 0,
                "timestamp": 1,
                "service": 1,
                "level": 1,
                "message": 1,
                "extra": 1
            }
        ).sort("timestamp", -1).limit(n)
        
        logs = await cursor.to_list(length=n)
        
        # Format timestamps for better readability
        for log in logs:
            if "timestamp" in log and isinstance(log["timestamp"], datetime):
                log["timestamp"] = log["timestamp"].isoformat()
        
        return {
            "count": len(logs),
            "requested": n,
            "filters": {
                "service": service,
                "level": level,
                "search": search
            },
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch log entries"
        )