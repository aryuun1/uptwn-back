
import uuid
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base

class Hall(Base):
    __tablename__ = "halls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False)
    name = Column(String(100), nullable=False)
    screen_type = Column(String(50), nullable=True) # nicethave: 'imax', 'regular', etc.
    capacity = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    venue = relationship("Venue", back_populates="halls")
    seats = relationship("Seat", back_populates="hall", cascade="all, delete-orphan")
    # time_slots will link to hall optionally
