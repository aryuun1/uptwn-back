
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title_id = Column(UUID(as_uuid=True), ForeignKey("titles.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False) # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    title = relationship("Title", back_populates="reviews")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False) # booking_confirmed, reminder, cancelled
    is_read = Column(Boolean, default=False)
    reference_id = Column(UUID(as_uuid=True), nullable=True) # Booking ID, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
