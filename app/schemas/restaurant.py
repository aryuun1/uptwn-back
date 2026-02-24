from __future__ import annotations

import re
from typing import List, Optional
from pydantic import BaseModel, UUID4, field_validator
from decimal import Decimal
from datetime import date, time, datetime


def _utc_to_ist(v):
    """
    Normalise a time string from the frontend and convert UTC → IST (UTC+5:30).

    JavaScript serialises time as part of an ISO datetime, producing strings
    like "12:18.638Z" or "06:30:00.000Z" (UTC).  We strip fractional seconds,
    detect the UTC marker (Z), and shift by +5:30 before pydantic parses.

    Strings without any timezone marker are assumed to already be IST and are
    returned as-is after ensuring HH:MM:SS format.

    Examples:
      "06:30:00.000Z"  → "12:00:00"   (UTC → IST)
      "12:18.638Z"     → "17:48:00"   (UTC → IST, missing :SS added first)
      "18:30:00+05:30" → "18:30:00"   (explicit IST offset, strip and keep)
      "12:00:00"       → "12:00:00"   (no tz marker → pass through as IST)
    """
    if not isinstance(v, str):
        return v

    # Strip milliseconds (.638, .000 …)
    v = re.sub(r"\.\d+", "", v)

    is_utc = v.endswith("Z")
    v = v.rstrip("Z")

    # Strip any explicit offset (+05:30 / -05:30) — treat remainder as local IST
    v = re.sub(r"[+-]\d{2}:\d{2}$", "", v)

    # Ensure HH:MM:SS (add :00 if only HH:MM was supplied)
    if re.fullmatch(r"\d{2}:\d{2}", v):
        v += ":00"

    if not is_utc:
        return v

    # Shift UTC → IST (+5 h 30 min)
    parts = v.split(":")
    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
    total_minutes = h * 60 + m + 330     # 330 = 5*60 + 30
    total_minutes %= 24 * 60             # keep within a single day
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Admin — Reusable slot management
# ---------------------------------------------------------------------------

class RestaurantSlotCreate(BaseModel):
    start_time: time
    end_time: time
    capacity: int
    slot_type: str                          # "lunch" | "dinner"
    discount_percent: Optional[Decimal] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def normalise_time(cls, v):
        return _utc_to_ist(v)


class RestaurantSlotAdmin(BaseModel):
    id: UUID4
    listing_id: UUID4
    start_time: time
    end_time: Optional[time] = None
    capacity: int
    slot_type: Optional[str] = None
    discount_percent: Optional[Decimal] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Public — Available slots for a date
# ---------------------------------------------------------------------------

class RestaurantSlotWindow(BaseModel):
    id: UUID4
    start_time: time
    end_time: Optional[time] = None
    slot_type: Optional[str] = None
    discount_percent: Optional[Decimal] = None
    available: int
    capacity: int
    is_full: bool


class RestaurantSlotGroup(BaseModel):
    slot_type: str              # "lunch" | "dinner"
    windows: List[RestaurantSlotWindow]


# ---------------------------------------------------------------------------
# Public — Booking / Reserve
# ---------------------------------------------------------------------------

class RestaurantBookingCreate(BaseModel):
    listing_id: UUID4
    time_slot_id: UUID4         # the reusable slot definition
    event_date: date            # the specific day the user wants to visit
    party_size: int
    booking_type: str           # "cover" | "reserve"
    notes: Optional[str] = None


class RestaurantBookingResponse(BaseModel):
    type: str                               # "booking" | "hold"
    id: UUID4
    listing_id: UUID4
    time_slot_id: UUID4
    slot_type: Optional[str] = None
    slot_date: date
    start_time: time
    end_time: Optional[time] = None
    party_size: int
    booking_type: str
    discount_percent: Optional[Decimal] = None
    cover_charge_paid: Decimal
    estimate: Decimal
    status: str                             # "confirmed" | "reserved"
    booking_number: Optional[str] = None   # cover bookings only
    expires_at: Optional[datetime] = None  # reserve holds only
    created_at: datetime
