"""
User Feedback API Endpoints

Allows users to submit feedback, bug reports, and feature requests.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.models.feedback import Feedback, FeedbackType, FeedbackStatus
from app.auth import get_current_user
from app.services.logging_service import logger


router = APIRouter(prefix="/api/feedback", tags=["feedback"])


# Pydantic schemas
class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    type: FeedbackType
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    page_url: Optional[str] = None
    browser_info: Optional[str] = None
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    feature_rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""
    id: int
    type: FeedbackType
    status: FeedbackStatus
    title: str
    description: str
    page_url: Optional[str]
    satisfaction_rating: Optional[int]
    feature_rating: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeedbackUpdate(BaseModel):
    """Schema for updating feedback (admin only)."""
    status: Optional[FeedbackStatus] = None
    admin_notes: Optional[str] = None
    assigned_to: Optional[str] = None


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit new feedback.

    Users can submit bug reports, feature requests, or general feedback.
    """
    feedback = Feedback(
        user_id=current_user.id,
        type=feedback_data.type,
        title=feedback_data.title,
        description=feedback_data.description,
        page_url=feedback_data.page_url,
        browser_info=feedback_data.browser_info,
        satisfaction_rating=feedback_data.satisfaction_rating,
        feature_rating=feedback_data.feature_rating,
        status=FeedbackStatus.NEW
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    logger.info(f"User {current_user.id} submitted feedback: {feedback.type} - {feedback.title}")

    return feedback


@router.get("", response_model=List[FeedbackResponse])
async def get_my_feedback(
    type: Optional[FeedbackType] = None,
    status: Optional[FeedbackStatus] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's feedback.

    Filter by type or status, return most recent first.
    """
    query = db.query(Feedback).filter(Feedback.user_id == current_user.id)

    if type:
        query = query.filter(Feedback.type == type)

    if status:
        query = query.filter(Feedback.status == status)

    feedback_list = query.order_by(Feedback.created_at.desc()).limit(limit).all()

    return feedback_list


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_detail(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed feedback by ID."""
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.user_id == current_user.id
    ).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    return feedback


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete feedback (user can only delete their own).
    """
    feedback = db.query(Feedback).filter(
        Feedback.id == feedback_id,
        Feedback.user_id == current_user.id
    ).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    db.delete(feedback)
    db.commit()

    return {"message": "Feedback deleted successfully"}


@router.get("/stats/summary")
async def get_feedback_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get feedback statistics for current user.
    """
    # Count by type
    type_counts = db.query(
        Feedback.type,
        func.count(Feedback.id).label('count')
    ).filter(
        Feedback.user_id == current_user.id
    ).group_by(Feedback.type).all()

    # Count by status
    status_counts = db.query(
        Feedback.status,
        func.count(Feedback.id).label('count')
    ).filter(
        Feedback.user_id == current_user.id
    ).group_by(Feedback.status).all()

    return {
        "by_type": {str(type_val): count for type_val, count in type_counts},
        "by_status": {str(status_val): count for status_val, count in status_counts},
        "total": sum(count for _, count in type_counts)
    }


# Admin endpoints (would need admin check middleware)
@router.get("/admin/all", response_model=List[FeedbackResponse])
async def get_all_feedback_admin(
    type: Optional[FeedbackType] = None,
    status: Optional[FeedbackStatus] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all feedback (admin only).

    Note: In production, add admin role check.
    """
    # TODO: Add admin check
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")

    query = db.query(Feedback)

    if type:
        query = query.filter(Feedback.type == type)

    if status:
        query = query.filter(Feedback.status == status)

    feedback_list = query.order_by(Feedback.created_at.desc()).limit(limit).all()

    return feedback_list


@router.put("/admin/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback_admin(
    feedback_id: int,
    update_data: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update feedback status (admin only).

    Note: In production, add admin role check.
    """
    # TODO: Add admin check

    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if update_data.status:
        feedback.status = update_data.status

        # Set resolved_at if status is completed or wont_fix
        if update_data.status in [FeedbackStatus.COMPLETED, FeedbackStatus.WONT_FIX]:
            feedback.resolved_at = datetime.utcnow()

    if update_data.admin_notes is not None:
        feedback.admin_notes = update_data.admin_notes

    if update_data.assigned_to is not None:
        feedback.assigned_to = update_data.assigned_to

    db.commit()
    db.refresh(feedback)

    return feedback
