
from typing import Optional, List
from pydantic import BaseModel, UUID4
from decimal import Decimal
from datetime import date, time, datetime

from app.schemas.venue import HallSummary


# Time Slot — Create (each item in the array)
class TimeSlotCreate(BaseModel):
    slot_date: date
    start_time: time
    end_time: time
    capacity: int
    price_override: Optional[Decimal] = None
    hall_id: Optional[UUID4] = None          # required for movies/events, omit for restaurants
    slot_type: Optional[str] = None          # "lunch" | "dinner" — restaurants only
    discount_percent: Optional[Decimal] = None  # restaurants only


# Time Slot — Update (admin PATCH /admin/time-slots/{id})
class TimeSlotUpdate(BaseModel):
    slot_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    capacity: Optional[int] = None
    price_override: Optional[Decimal] = None
    hall_id: Optional[UUID4] = None
    slot_type: Optional[str] = None
    discount_percent: Optional[Decimal] = None
    is_active: Optional[bool] = None


# Time Slot — DB response
class TimeSlot(BaseModel):
    id: UUID4
    listing_id: UUID4
    hall_id: Optional[UUID4] = None
    slot_date: Optional[date] = None   # NULL for reusable restaurant slots
    start_time: time
    end_time: Optional[time] = None
    capacity: int
    booked_count: int = 0
    price_override: Optional[Decimal] = None
    slot_type: Optional[str] = None
    discount_percent: Optional[Decimal] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# Time Slot with nested hall — used in user-facing responses (Screen 5)
class TimeSlotWithHall(TimeSlot):
    hall: Optional[HallSummary] = None

    class Config:
        from_attributes = True


# Compact time slot for booking responses
class TimeSlotSummary(BaseModel):
    slot_date: date
    start_time: time
    end_time: Optional[time] = None

    class Config:
        from_attributes = True


# Response for GET /listings/{id}/time-slots (Screen 5)
class TimeSlotListResponse(BaseModel):
    listing_id: UUID4
    date: date
    time_slots: List[TimeSlotWithHall]


# Hall schedule entry — used in GET /admin/halls/{id}/schedule
class HallScheduleEntry(BaseModel):
    id: UUID4
    listing_id: UUID4
    title_name: str
    slot_date: date
    start_time: time
    end_time: Optional[time] = None
    capacity: int
    booked_count: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True


class HallScheduleResponse(BaseModel):
    hall_id: UUID4
    hall_name: str
    date: date
    slots: List[HallScheduleEntry]


# Bulk time slot generation — one slot definition repeated across a date range
class BulkSlotDefinition(BaseModel):
    start_time: time
    end_time: time
    capacity: int
    hall_id: Optional[UUID4] = None          # movies/events
    slot_type: Optional[str] = None          # "lunch" | "dinner" — restaurants
    price_override: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None  # restaurants


class BulkTimeSlotCreate(BaseModel):
    date_from: date
    date_to: date
    days: List[str]  # e.g. ["mon", "wed", "fri"] or ["sat", "sun"]
    slots: List[BulkSlotDefinition]


class BulkCreateResult(BaseModel):
    created: int
    skipped: int


# ---------------------------------------------------------------------------
# Bulk Listing Upload — cross-venue, cross-hall, cross-date in one request
# ---------------------------------------------------------------------------

class BulkListingSlotInput(BaseModel):
    """One timeslot row inside a bulk-listing entry."""
    hall_id: UUID4
    slot_date: date
    start_time: time
    end_time: time
    capacity: int
    price_override: Optional[Decimal] = None
    slot_type: Optional[str] = None          # "lunch" | "dinner" — not for cinemas
    discount_percent: Optional[Decimal] = None


class BulkListingEntry(BaseModel):
    """One venue/cinema row in the bulk upload modal."""
    venue_id: UUID4
    price: Optional[Decimal] = None
    currency: str = "INR"
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    total_capacity: Optional[int] = None
    slots: List[BulkListingSlotInput]


class BulkListingCreate(BaseModel):
    """
    Request body for POST /admin/titles/{title_id}/bulk-listings.

    on_conflict behaviour:
      "skip"  — conflicting slots are silently skipped; everything else is committed.
      "fail"  — if ANY hall conflict or validation error is found the entire
                request is rejected (HTTP 409) with full conflict details so the
                admin can correct the modal and resubmit.
    """
    entries: List[BulkListingEntry]
    on_conflict: str = "skip"   # "skip" | "fail"


# --- Response models ---

class SlotBulkResult(BaseModel):
    hall_id: UUID4
    hall_name: str
    slot_date: date
    start_time: time
    end_time: time
    status: str                          # "created" | "conflict" | "past" | "duplicate"
    slot_id: Optional[UUID4] = None      # populated when status == "created"
    conflict_detail: Optional[str] = None


class ListingBulkResult(BaseModel):
    venue_id: UUID4
    venue_name: str
    city: str
    listing_status: str                  # "created" | "skipped"
    listing_id: Optional[UUID4] = None
    skip_reason: Optional[str] = None
    slots: List[SlotBulkResult] = []


class BulkListingSummary(BaseModel):
    total_entries: int
    listings_created: int
    listings_skipped: int
    slots_created: int
    slots_skipped: int
    conflict_count: int


class BulkListingResponse(BaseModel):
    summary: BulkListingSummary
    results: List[ListingBulkResult]
