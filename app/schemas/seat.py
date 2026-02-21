
from typing import Annotated, Optional, List
from pydantic import BaseModel, Field, UUID4
from decimal import Decimal
from datetime import datetime

from app.schemas.venue import HallSummary


# Seat — base fields
class SeatBase(BaseModel):
    row_label: str
    seat_number: int
    category: str
    price: Decimal
    is_aisle: bool = False
    is_accessible: bool = False


class SeatCreate(SeatBase):
    pass


class SeatUpdate(BaseModel):
    category: Optional[str] = None
    price: Optional[Decimal] = None
    is_aisle: Optional[bool] = None
    is_accessible: Optional[bool] = None


class Seat(SeatBase):
    id: UUID4
    hall_id: UUID4

    class Config:
        from_attributes = True


# Bulk seat creation (POST /admin/halls/{id}/seats/bulk)
class SeatBulkCreate(BaseModel):
    seats: List[SeatCreate]


class SeatBulkCreateResponse(BaseModel):
    created_count: int
    hall_id: UUID4


# --- Seat Map (user-facing, Screen 6) ---

class SeatStatus(BaseModel):
    id: UUID4
    number: int
    status: str  # available, booked, locked
    is_aisle: bool
    is_accessible: bool


class SeatRow(BaseModel):
    label: str
    category: str
    price: Decimal
    seats: List[SeatStatus]


class SeatMapResponse(BaseModel):
    time_slot_id: UUID4
    hall: HallSummary
    rows: List[SeatRow]


# --- Seat Locking (Screen 6) ---

class SeatLockRequest(BaseModel):
    seat_ids: Annotated[List[UUID4], Field(min_length=1, max_length=10)]


class SeatLockResponse(BaseModel):
    locked_seats: List[UUID4]
    locked_until: datetime
    ttl_seconds: int


class SeatLockReleaseResponse(BaseModel):
    released_seats: List[UUID4]


# --- Capacity Holds — restaurants (Screen 6B) ---

class HoldRequest(BaseModel):
    quantity: int


class HoldResponse(BaseModel):
    hold_id: UUID4
    time_slot_id: UUID4
    quantity: int
    expires_at: datetime
    ttl_seconds: int
    remaining_capacity: int


class HoldReleaseResponse(BaseModel):
    released_quantity: int
    time_slot_id: UUID4
