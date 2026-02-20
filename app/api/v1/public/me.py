from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.review_notification import Notification
from app.schemas.user import User as UserSchema, UserUpdate
from app.schemas.review_notification import Notification as NotificationSchema
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/me", tags=["Me"])


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("/", response_model=UserSchema)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/", response_model=UserSchema)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's profile (full_name, phone, avatar_url)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@router.get("/notifications", response_model=PaginatedResponse[NotificationSchema])
def list_notifications(
    unread_only: bool = Query(False, description="Return only unread notifications"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's notifications, newest first."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.is_read == False)  # noqa: E712

    total = query.count()
    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        data=notifications,
        total=total,
        page=page,
        limit=limit,
        total_pages=-(-total // limit) if total else 0,
    )


@router.patch("/notifications/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications for the current user as read."""
    updated = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    ).update({"is_read": True}, synchronize_session="fetch")
    db.commit()
    return {"marked_read": updated}


@router.patch("/notifications/{notif_id}/read", response_model=NotificationSchema)
def mark_notification_read(
    notif_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif
