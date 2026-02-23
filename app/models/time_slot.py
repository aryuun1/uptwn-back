
import uuid
from sqlalchemy import Column, String, Boolean, Date, Time, Integer, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base

class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True)
    hall_id = Column(UUID(as_uuid=True), ForeignKey("halls.id"), nullable=True, index=True)
    slot_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)
    capacity = Column(Integer, nullable=False)
    booked_count = Column(Integer, default=0)
    price_override = Column(DECIMAL(10, 2), nullable=True)
    slot_type = Column(String(20), nullable=True)       # "lunch" | "dinner" — restaurants only
    discount_percent = Column(DECIMAL(5, 2), nullable=True)  # e.g. 30.00 — restaurants only
    is_active = Column(Boolean, default=True)

    # Relationships
    listing = relationship("Listing", back_populates="time_slots")
    # hall relation is optional but useful
    hall = relationship("Hall")
    seat_availability = relationship("SeatAvailability", back_populates="time_slot", cascade="all, delete-orphan")
    booking_holds = relationship("BookingHold", back_populates="time_slot", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="time_slot")
