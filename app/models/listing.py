
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, DECIMAL, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base

class Listing(Base):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title_id = Column(UUID(as_uuid=True), ForeignKey("titles.id"), nullable=False)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    price = Column(DECIMAL(10, 2), nullable=True)
    currency = Column(String(3), default="INR")
    start_datetime = Column(DateTime(timezone=True), nullable=True)
    end_datetime = Column(DateTime(timezone=True), nullable=True)
    total_capacity = Column(Integer, nullable=True)
    booked_count = Column(Integer, default=0)
    status = Column(String(20), default="active", index=True) # active, draft, etc.
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    title = relationship("Title", back_populates="listings")
    venue = relationship("Venue", back_populates="listings")
    time_slots = relationship("TimeSlot", back_populates="listing", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="listing")
