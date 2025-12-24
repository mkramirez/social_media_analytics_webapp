"""API Profile management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.profile import APIProfile
from app.models.schemas import (
    APIProfileCreate,
    APIProfileResponse,
    APIProfileWithCredentials,
    APIProfileUpdate,
    MessageResponse
)
from app.middleware.auth import get_current_active_user
from app.services.credential_service import CredentialService

router = APIRouter()
credential_service = CredentialService()


@router.post("/", response_model=APIProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: APIProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API credential profile.

    Credentials are encrypted before storage.

    Args:
        profile_data: Profile creation data
        current_user: Authenticated user
        db: Database session

    Returns:
        Created profile (without credentials)
    """
    # Validate credentials for the platform
    is_valid, error = credential_service.validate_credentials(
        profile_data.platform,
        profile_data.credentials
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid credentials: {error}"
        )

    # Check if profile name already exists for this user/platform
    existing = db.query(APIProfile).filter(
        APIProfile.user_id == current_user.id,
        APIProfile.platform == profile_data.platform,
        APIProfile.profile_name == profile_data.profile_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile '{profile_data.profile_name}' already exists for {profile_data.platform}"
        )

    # Encrypt credentials
    encrypted_creds = credential_service.encrypt_credentials(profile_data.credentials)

    # Create profile
    new_profile = APIProfile(
        user_id=current_user.id,
        profile_name=profile_data.profile_name,
        platform=profile_data.platform,
        encrypted_credentials=encrypted_creds,
        is_active=True
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return APIProfileResponse.from_orm(new_profile)


@router.get("/", response_model=List[APIProfileResponse])
async def list_profiles(
    platform: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all API profiles for the current user.

    Args:
        platform: Optional platform filter
        current_user: Authenticated user
        db: Database session

    Returns:
        List of profiles (without credentials)
    """
    query = db.query(APIProfile).filter(APIProfile.user_id == current_user.id)

    if platform:
        query = query.filter(APIProfile.platform == platform)

    profiles = query.order_by(APIProfile.created_at.desc()).all()

    return [APIProfileResponse.from_orm(p) for p in profiles]


@router.get("/{profile_id}", response_model=APIProfileWithCredentials)
async def get_profile(
    profile_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific profile with decrypted credentials.

    Args:
        profile_id: Profile UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Profile with decrypted credentials
    """
    profile = db.query(APIProfile).filter(
        APIProfile.id == profile_id,
        APIProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    # Decrypt credentials
    try:
        decrypted_creds = credential_service.decrypt_credentials(profile.encrypted_credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt credentials: {str(e)}"
        )

    # Create response with credentials
    response_data = APIProfileResponse.from_orm(profile).dict()
    response_data["credentials"] = decrypted_creds

    return APIProfileWithCredentials(**response_data)


@router.put("/{profile_id}", response_model=APIProfileResponse)
async def update_profile(
    profile_id: UUID,
    profile_data: APIProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an API profile.

    Args:
        profile_id: Profile UUID
        profile_data: Update data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated profile
    """
    profile = db.query(APIProfile).filter(
        APIProfile.id == profile_id,
        APIProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    # Update profile name if provided
    if profile_data.profile_name:
        # Check for duplicates
        existing = db.query(APIProfile).filter(
            APIProfile.user_id == current_user.id,
            APIProfile.platform == profile.platform,
            APIProfile.profile_name == profile_data.profile_name,
            APIProfile.id != profile_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Profile name '{profile_data.profile_name}' already exists"
            )

        profile.profile_name = profile_data.profile_name

    # Update credentials if provided
    if profile_data.credentials:
        # Validate new credentials
        is_valid, error = credential_service.validate_credentials(
            profile.platform,
            profile_data.credentials
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid credentials: {error}"
            )

        # Encrypt new credentials
        encrypted_creds = credential_service.encrypt_credentials(profile_data.credentials)
        profile.encrypted_credentials = encrypted_creds

    # Update active status if provided
    if profile_data.is_active is not None:
        profile.is_active = profile_data.is_active

    db.commit()
    db.refresh(profile)

    return APIProfileResponse.from_orm(profile)


@router.delete("/{profile_id}", response_model=MessageResponse)
async def delete_profile(
    profile_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an API profile.

    Args:
        profile_id: Profile UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    profile = db.query(APIProfile).filter(
        APIProfile.id == profile_id,
        APIProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    db.delete(profile)
    db.commit()

    return MessageResponse(
        message="Profile deleted successfully",
        detail=f"Deleted profile: {profile.profile_name}"
    )


@router.get("/platform/{platform}/active", response_model=APIProfileWithCredentials)
async def get_active_profile_for_platform(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the active profile for a specific platform.

    Args:
        platform: Platform name
        current_user: Authenticated user
        db: Database session

    Returns:
        Active profile with credentials
    """
    profile = db.query(APIProfile).filter(
        APIProfile.user_id == current_user.id,
        APIProfile.platform == platform,
        APIProfile.is_active == True
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active profile found for {platform}"
        )

    # Decrypt credentials
    try:
        decrypted_creds = credential_service.decrypt_credentials(profile.encrypted_credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt credentials: {str(e)}"
        )

    # Create response with credentials
    response_data = APIProfileResponse.from_orm(profile).dict()
    response_data["credentials"] = decrypted_creds

    return APIProfileWithCredentials(**response_data)
