
import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, func, Text, DECIMAL, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.db.session import Base

class   CategoryType(str, enum.Enum):
    movies = "movies"
    events = "events"
    restaurants = "restaurants"

class Title(Base):
    __tablename__ = "titles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(Enum(CategoryType, name="category_type"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    image_url = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    tags = Column(ARRAY(Text), nullable=True) # Needs GIN index manually in migration
    meta = Column(JSONB, nullable=True) # Genre, cuisine, etc. renamed from metadata (reserved)
    rating = Column(DECIMAL(2, 1), default=0.0)
    rating_count = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    images = relationship("TitleImage", back_populates="title", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="title", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="title")

class TitleImage(Base):
    __tablename__ = "title_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title_id = Column(UUID(as_uuid=True), ForeignKey("titles.id"), nullable=False)
    image_url = Column(Text, nullable=False)
    display_order = Column(Integer, default=0)
    caption = Column(String(255), nullable=True)

    title = relationship("Title", back_populates="images")
