
import uuid
from sqlalchemy import Column, String, Boolean, Integer, DECIMAL, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base

class Seat(Base):
    __tablename__ = "seats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hall_id = Column(UUID(as_uuid=True), ForeignKey("halls.id"), nullable=False, index=True)
    row_label = Column(String(5), nullable=False)
    seat_number = Column(Integer, nullable=False)
    category = Column(String(20), nullable=False) # platinum, gold, etc.
    price = Column(DECIMAL(10, 2), nullable=False)
    is_aisle = Column(Boolean, default=False)
    is_accessible = Column(Boolean, default=False)

    hall = relationship("Hall", back_populates="seats")
    availabilities = relationship("SeatAvailability", back_populates="seat", cascade="all, delete-orphan")

class SeatAvailability(Base):
    __tablename__ = "seat_availability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time_slot_id = Column(UUID(as_uuid=True), ForeignKey("time_slots.id"), nullable=False, index=True)
    seat_id = Column(UUID(as_uuid=True), ForeignKey("seats.id"), nullable=False, index=True)
    status = Column(String(20), default="available", index=True) # available, booked, locked
    locked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True, index=True)

    time_slot = relationship("TimeSlot", back_populates="seat_availability")
    seat = relationship("Seat", back_populates="availabilities")
