
import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, func, Text, DECIMAL, Integer, ARRAY, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base

class VenueType(str, enum.Enum):
    CINEMA = "Cinema"
    STADIUM = "Stadium"
    HALL = "Hall"
    RESTAURANT = "Restaurant"
    OUTDOOR = "Outdoor"

class Venue(Base):
    __tablename__ = "venues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(SAEnum(VenueType, native_enum=False), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=False, index=True)
    capacity = Column(Integer, nullable=True)
    amenities = Column(ARRAY(Text), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    image_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    halls = relationship("Hall", back_populates="venue", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="venue")
