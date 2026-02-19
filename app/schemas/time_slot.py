
from typing import Optional, List
from pydantic import BaseModel, UUID4
from decimal import Decimal
from datetime import date, time

from app.schemas.venue import HallSummary


# Time Slot — Create (each item in the bulk array)
class TimeSlotCreate(BaseModel):
    slot_date: date
    start_time: time
    end_time: time
    capacity: int
    price_override: Optional[Decimal] = None
    hall_id: UUID4


# Time Slot — Update (admin PATCH /admin/time-slots/{id})
class TimeSlotUpdate(BaseModel):
    slot_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    capacity: Optional[int] = None
    price_override: Optional[Decimal] = None
    hall_id: Optional[UUID4] = None
    is_active: Optional[bool] = None


# Time Slot — DB response
class TimeSlot(BaseModel):
    id: UUID4
    listing_id: UUID4
    hall_id: Optional[UUID4] = None
    slot_date: date
    start_time: time
    end_time: Optional[time] = None
    capacity: int
    booked_count: int = 0
    price_override: Optional[Decimal] = None
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
