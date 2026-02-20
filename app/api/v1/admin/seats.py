
from uuid import UUID
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_admin_user, get_current_user
from app.models.user import User
from app.models.hall import Hall
from app.models.seat import Seat, SeatAvailability
from app.models.time_slot import TimeSlot
from app.schemas.seat import (
    SeatCreate,
    SeatUpdate,
    Seat as SeatSchema,
    SeatBulkCreate,
    SeatBulkCreateResponse,
)

seats_router = APIRouter(prefix="/admin/halls", tags=["Admin - Seats"])
seat_router = APIRouter(prefix="/admin/seats", tags=["Admin - Seats"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _future_active_slots(db: Session, hall_id: UUID) -> List[TimeSlot]:
    """Return all future active time slots for a given hall."""
    today = datetime.now(timezone.utc).date()
    return (
        db.query(TimeSlot)
        .filter(
            TimeSlot.hall_id == hall_id,
            TimeSlot.is_active == True,
            TimeSlot.slot_date >= today,
        )
        .all()
    )


def _seed_availability(db: Session, seat: Seat, slots: List[TimeSlot]):
    """Insert SeatAvailability rows for a seat across a list of time slots."""
    for slot in slots:
        db.add(SeatAvailability(
            time_slot_id=slot.id,
            seat_id=seat.id,
            status="available",
        ))


# ---------------------------------------------------------------------------
# Single seat creation
# ---------------------------------------------------------------------------


@seats_router.post(
    "/{hall_id}/seats",
    response_model=SeatSchema,
    status_code=status.HTTP_201_CREATED,
)
def create_seat(
    hall_id: UUID,
    data: SeatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    hall = db.query(Hall).filter(Hall.id == hall_id, Hall.is_active == True).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Hall not found")

    seat = Seat(hall_id=hall_id, **data.model_dump())
    db.add(seat)
    db.flush()

    # Seed availability for any existing future time slots
    slots = _future_active_slots(db, hall_id)
    _seed_availability(db, seat, slots)

    db.commit()
    db.refresh(seat)
    return seat


# ---------------------------------------------------------------------------
# Bulk seat creation
# ---------------------------------------------------------------------------


@seats_router.post(
    "/{hall_id}/seats/bulk",
    response_model=SeatBulkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def bulk_create_seats(
    hall_id: UUID,
    data: SeatBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    hall = db.query(Hall).filter(Hall.id == hall_id, Hall.is_active == True).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Hall not found")

    if not data.seats:
        raise HTTPException(status_code=400, detail="seats list cannot be empty")

    # Load once — shared across all new seats
    slots = _future_active_slots(db, hall_id)

    new_seats = []
    for seat_data in data.seats:
        seat = Seat(hall_id=hall_id, **seat_data.model_dump())
        db.add(seat)
        db.flush()
        new_seats.append(seat)
        _seed_availability(db, seat, slots)

    db.commit()
    return SeatBulkCreateResponse(created_count=len(new_seats), hall_id=hall_id)


# ---------------------------------------------------------------------------
# List seats in a hall
# ---------------------------------------------------------------------------


@seats_router.get("/{hall_id}/seats", response_model=List[SeatSchema])
def list_seats(
    hall_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hall = db.query(Hall).filter(Hall.id == hall_id, Hall.is_active == True).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Hall not found")

    return (
        db.query(Seat)
        .filter(Seat.hall_id == hall_id)
        .order_by(Seat.row_label, Seat.seat_number)
        .all()
    )


# ---------------------------------------------------------------------------
# Update / delete a single seat
# ---------------------------------------------------------------------------


@seat_router.patch("/{seat_id}", response_model=SeatSchema)
def update_seat(
    seat_id: UUID,
    data: SeatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(seat, field, value)

    db.commit()
    db.refresh(seat)
    return seat


@seat_router.delete("/{seat_id}", status_code=status.HTTP_200_OK)
def delete_seat(
    seat_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    seat = db.query(Seat).filter(Seat.id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat not found")

    # SeatAvailability rows cascade-delete via the ORM relationship
    db.delete(seat)
    db.commit()
    return {"id": str(seat_id), "deleted": True}
