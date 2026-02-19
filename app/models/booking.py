
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, DECIMAL, Integer, ForeignKey, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True)
    time_slot_id = Column(UUID(as_uuid=True), ForeignKey("time_slots.id"), nullable=True, index=True)
    booking_number = Column(String(20), unique=True, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(20), default="confirmed", index=True) # confirmed, cancelled, completed, pending
    booking_date = Column(DateTime(timezone=True), server_default=func.now())
    event_date = Column(Date, nullable=True) # For quick access
    notes = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    listing = relationship("Listing", back_populates="bookings")
    time_slot = relationship("TimeSlot", back_populates="bookings")
    seats = relationship("BookingSeat", back_populates="booking", cascade="all, delete-orphan")

class BookingSeat(Base):
    __tablename__ = "booking_seats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, index=True)
    seat_id = Column(UUID(as_uuid=True), ForeignKey("seats.id"), nullable=False)
    time_slot_id = Column(UUID(as_uuid=True), ForeignKey("time_slots.id"), nullable=False) # Disambiguation

    booking = relationship("Booking", back_populates="seats")
    seat = relationship("Seat")
    time_slot = relationship("TimeSlot")

class BookingHold(Base):
    __tablename__ = "booking_holds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    time_slot_id = Column(UUID(as_uuid=True), ForeignKey("time_slots.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    time_slot = relationship("TimeSlot", back_populates="booking_holds")
