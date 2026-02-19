
from typing import Optional, List
from pydantic import BaseModel, UUID4
from decimal import Decimal
from datetime import datetime


# Hall Schemas
class HallBase(BaseModel):
    name: str
    screen_type: Optional[str] = None
    capacity: int


class HallCreate(HallBase):
    pass


class HallUpdate(BaseModel):
    name: Optional[str] = None
    screen_type: Optional[str] = None
    capacity: Optional[int] = None


class Hall(HallBase):
    id: UUID4
    venue_id: UUID4
    is_active: bool

    class Config:
        from_attributes = True


# Compact hall for nested responses (time slot, seat map)
class HallSummary(BaseModel):
    id: UUID4
    name: str
    screen_type: Optional[str] = None

    class Config:
        from_attributes = True


from app.models.venue import VenueType

# Venue Schemas
class VenueBase(BaseModel):
    name: str
    type: VenueType
    address: Optional[str] = None
    city: str
    capacity: Optional[int] = None
    amenities: Optional[List[str]] = None
    contact_phone: Optional[str] = None
    image_url: Optional[str] = None


class VenueCreate(VenueBase):
    pass


class VenueUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[VenueType] = None
    address: Optional[str] = None
    city: Optional[str] = None
    capacity: Optional[int] = None
    amenities: Optional[List[str]] = None
    contact_phone: Optional[str] = None
    image_url: Optional[str] = None


class Venue(VenueBase):
    id: UUID4
    is_active: bool
    created_at: datetime
    halls: List[Hall] = []

    class Config:
        from_attributes = True


# Compact venue for nested responses (listing, booking)
class VenueSummary(BaseModel):
    id: UUID4
    name: str
    city: str
    type: VenueType
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


# Admin venue list item (includes halls_count)
class VenueListItem(VenueBase):
    id: UUID4
    is_active: bool
    halls_count: int = 0

    class Config:
        from_attributes = True
