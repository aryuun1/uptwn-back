
from typing import Optional
from pydantic import BaseModel, UUID4
from datetime import datetime


class ReviewBase(BaseModel):
    rating: int
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class Review(ReviewBase):
    id: UUID4
    user_id: UUID4
    title_id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    title: str
    message: str
    type: str
    reference_id: Optional[UUID4] = None


class Notification(NotificationBase):
    id: UUID4
    user_id: UUID4
    is_read: bool = False
    created_at: datetime

    class Config:
        from_attributes = True
