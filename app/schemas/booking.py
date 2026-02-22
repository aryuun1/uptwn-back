
from __future__ import annotations

from typing import Annotated, Optional, List
from pydantic import BaseModel, Field, UUID4, field_validator
from decimal import Decimal
from datetime import date, datetime


# Booking — Create (POST /bookings)
class BookingCreate(BaseModel):
    listing_id: UUID4
    time_slot_id: Optional[UUID4] = None
    seat_ids: Annotated[List[UUID4], Field(max_length=10)] = []
    quantity: int = 1
    event_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("time_slot_id", mode="before")
    @classmethod
    def parse_empty_str_to_none(cls, v):
        if v == "":
            return None
        return v


# Nested response objects for booking responses
class BookingListingSummary(BaseModel):
    title: str
    image_url: Optional[str] = None
    category: Optional[str] = None


class BookingVenueSummary(BaseModel):
    name: str
    city: str


class BookingTimeSlotSummary(BaseModel):
    slot_date: date
    start_time: str
    end_time: Optional[str] = None
    hall_id: Optional[UUID4] = None
    hall_name: Optional[str] = None


class BookingSeatResponse(BaseModel):
    row: str
    number: int
    category: str
    price: Optional[Decimal] = None


# Booking — Full response (POST /bookings, GET /bookings/{id})
class Booking(BaseModel):
    id: UUID4
    booking_number: str
    listing_id: UUID4
    time_slot_id: Optional[UUID4] = None
    quantity: int
    total_amount: Decimal
    status: str
    booking_date: datetime
    event_date: Optional[date] = None
    notes: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    listing: Optional[BookingListingSummary] = None
    venue: Optional[BookingVenueSummary] = None
    time_slot: Optional[BookingTimeSlotSummary] = None
    seats: List[BookingSeatResponse] = []

    class Config:
        from_attributes = True


# Booking — Cancel response (PATCH /bookings/{id}/cancel)
class BookingCancelResponse(BaseModel):
    id: UUID4
    booking_number: str
    status: str
    cancelled_at: datetime


# Booking — Admin view (GET /admin/bookings, includes user info)
class AdminBooking(Booking):
    user: Optional[UserSummary] = None

    class Config:
        from_attributes = True


# Import at the bottom to avoid circular imports
from app.schemas.user import UserSummary  # noqa: E402

AdminBooking.model_rebuild()
