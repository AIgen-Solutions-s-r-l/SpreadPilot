from app.api.v1.endpoints.auth import User, get_current_user
from app.db.mongodb import get_db
from app.schemas.follower import FollowerCreate, FollowerResponse, FollowerUpdate
from app.services.follower_service import FollowerService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from spreadpilot_core.logging.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=list[FollowerResponse])
async def get_followers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get all followers with optional filtering by status.
    """
    try:
        follower_service = FollowerService(db=db)
        followers = await follower_service.get_followers(
            skip=skip, limit=limit, status=status
        )
        return followers
    except Exception as e:
        logger.error(f"Error getting followers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting followers: {e!s}",
        )


@router.get("/{follower_id}", response_model=FollowerResponse)
async def get_follower(
    follower_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Get a specific follower by ID.
    """
    try:
        follower_service = FollowerService(db=db)
        follower = await follower_service.get_follower(follower_id)
        if not follower:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Follower with ID {follower_id} not found",
            )
        return follower
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting follower {follower_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting follower: {e!s}",
        )


@router.post("/", response_model=FollowerResponse, status_code=status.HTTP_201_CREATED)
async def create_follower(
    follower: FollowerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Create a new follower.
    """
    try:
        follower_service = FollowerService(db=db)

        # Check if follower with same email already exists
        existing_follower = await follower_service.get_follower_by_email(follower.email)
        if existing_follower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Follower with email {follower.email} already exists",
            )

        # Create follower
        created_follower = await follower_service.create_follower(follower)
        return created_follower
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating follower: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating follower: {e!s}",
        )


@router.put("/{follower_id}", response_model=FollowerResponse)
async def update_follower(
    follower_id: str,
    follower_update: FollowerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Update a follower.
    """
    try:
        follower_service = FollowerService(db=db)

        # Check if follower exists
        existing_follower = await follower_service.get_follower(follower_id)
        if not existing_follower:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Follower with ID {follower_id} not found",
            )

        # Update follower
        updated_follower = await follower_service.update_follower(
            follower_id, follower_update
        )
        return updated_follower
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating follower {follower_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating follower: {e!s}",
        )


@router.delete("/{follower_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_follower(
    follower_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Delete a follower.
    """
    try:
        follower_service = FollowerService(db=db)

        # Check if follower exists
        existing_follower = await follower_service.get_follower(follower_id)
        if not existing_follower:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Follower with ID {follower_id} not found",
            )

        # Delete follower
        await follower_service.delete_follower(follower_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting follower {follower_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting follower: {e!s}",
        )
