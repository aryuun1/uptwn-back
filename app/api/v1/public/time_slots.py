from uuid import UUID
from typing import List, Optional
from datetime import date, datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sqlfunc, and_, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.listing import Listing
from app.models.time_slot import TimeSlot
from app.models.hall import Hall
from app.models.seat import Seat, SeatAvailability
from app.models.booking import BookingHold
from app.schemas.time_slot import TimeSlotWithHall
from app.schemas.seat import (
    SeatMapResponse,
    SeatRow,
    SeatStatus,
    SeatLockRequest,
    SeatLockResponse,
    SeatLockReleaseResponse,
    HoldRequest,
    HoldResponse,
    HoldReleaseResponse,
)
from app.schemas.venue import HallSummary
from app.utils.timeslots import deactivate_past_slots

listing_slots_router = APIRouter(prefix="/listings", tags=["Time Slots"])
slot_public_router = APIRouter(prefix="/time-slots", tags=["Time Slots"])

SEAT_LOCK_MINUTES = 10
HOLD_MINUTES = 10


# ---------------------------------------------------------------------------
# Public: time slots for a listing (date picker screen)
# ---------------------------------------------------------------------------


@listing_slots_router.get("/{listing_id}/time-slots", response_model=List[TimeSlotWithHall])
def get_listing_time_slots(
    listing_id: UUID,
    date: Optional[date] = Query(None, description="Filter by specific date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Return active, upcoming time slots for a listing.
    Optionally filter by a specific date.
    Used on the date/time picker screen before seat selection.
    """
    listing = (
        db.query(Listing)
        .filter(Listing.id == listing_id, Listing.status == "active")
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Expire any past slots before returning results
    deactivate_past_slots(db)

    # Use local time — slot_date/start_time are stored as timezone-naive local values
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    query = db.query(TimeSlot).filter(
        TimeSlot.listing_id == listing_id,
        TimeSlot.is_active == True,
        # Exclude slots that have already started:
        # keep only future dates, or today's slots whose start_time is still ahead
        or_(
            TimeSlot.slot_date > today,
            and_(
                TimeSlot.slot_date == today,
                TimeSlot.start_time >= current_time,
            ),
        ),
    )
    if date:
        query = query.filter(TimeSlot.slot_date == date)

    return query.order_by(TimeSlot.slot_date, TimeSlot.start_time).all()


# ---------------------------------------------------------------------------
# Public: Seat map (seat selection screen)
# ---------------------------------------------------------------------------


@slot_public_router.get("/{slot_id}/seat-map", response_model=SeatMapResponse)
def get_seat_map(
    slot_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Returns the seat map for a time slot, grouped by row.
    Expired seat locks are auto-released before the response is built.
    Does not require authentication — anyone can view availability.
    """
    slot = (
        db.query(TimeSlot)
        .filter(TimeSlot.id == slot_id, TimeSlot.is_active == True)
        .first()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")
    if not slot.hall_id:
        raise HTTPException(
            status_code=400,
            detail="This time slot does not have a hall — use capacity hold instead",
        )

    hall = db.query(Hall).filter(Hall.id == slot.hall_id, Hall.is_active == True).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Hall not found")

    # Auto-release expired seat locks
    now = datetime.now(timezone.utc)
    db.query(SeatAvailability).filter(
        SeatAvailability.time_slot_id == slot_id,
        SeatAvailability.status == "locked",
        SeatAvailability.locked_until < now,
    ).update(
        {"status": "available", "locked_by": None, "locked_until": None},
        synchronize_session="fetch",
    )
    db.commit()

    # Fetch all seats in this hall, ordered for rendering
    seats = (
        db.query(Seat)
        .filter(Seat.hall_id == slot.hall_id)
        .order_by(Seat.row_label, Seat.seat_number)
        .all()
    )

    # Build seat_id → availability lookup
    avail_map = {
        a.seat_id: a
        for a in db.query(SeatAvailability)
        .filter(SeatAvailability.time_slot_id == slot_id)
        .all()
    }

    # Group seats by row_label
    rows_dict: dict[str, dict] = {}
    for seat in seats:
        avail = avail_map.get(seat.id)
        seat_obj = SeatStatus(
            id=seat.id,
            number=seat.seat_number,
            status=avail.status if avail else "available",
            is_aisle=seat.is_aisle,
            is_accessible=seat.is_accessible,
        )
        key = seat.row_label
        if key not in rows_dict:
            rows_dict[key] = {
                "label": seat.row_label,
                "category": seat.category,
                "price": seat.price,
                "seats": [],
            }
        rows_dict[key]["seats"].append(seat_obj)

    return SeatMapResponse(
        time_slot_id=slot_id,
        hall=HallSummary(id=hall.id, name=hall.name, screen_type=hall.screen_type),
        rows=[SeatRow(**r) for r in rows_dict.values()],
    )


# ---------------------------------------------------------------------------
# Seat Locking (auth required)
# ---------------------------------------------------------------------------


@slot_public_router.post(
    "/{slot_id}/seats/lock",
    response_model=SeatLockResponse,
    status_code=status.HTTP_200_OK,
)
def lock_seats(
    slot_id: UUID,
    body: SeatLockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lock a set of seats for the authenticated user.
    Locks expire after 10 minutes. Re-locking already-locked seats
    (by the same user) extends the TTL.
    """
    slot = db.query(TimeSlot).filter(TimeSlot.id == slot_id, TimeSlot.is_active == True).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")
    if not slot.hall_id:
        raise HTTPException(status_code=400, detail="This slot has no hall — use capacity hold")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=SEAT_LOCK_MINUTES)

    # Validate all seats belong to this hall
    seats = db.query(Seat).filter(
        Seat.id.in_(body.seat_ids),
        Seat.hall_id == slot.hall_id,
    ).all()
    if len(seats) != len(body.seat_ids):
        raise HTTPException(status_code=400, detail="One or more seats do not belong to this hall")

    # Auto-release expired locks first
    db.query(SeatAvailability).filter(
        SeatAvailability.time_slot_id == slot_id,
        SeatAvailability.status == "locked",
        SeatAvailability.locked_until < now,
    ).update(
        {"status": "available", "locked_by": None, "locked_until": None},
        synchronize_session="fetch",
    )

    # Check availability of requested seats
    avail_map = {
        a.seat_id: a
        for a in db.query(SeatAvailability).filter(
            SeatAvailability.time_slot_id == slot_id,
            SeatAvailability.seat_id.in_(body.seat_ids),
        ).all()
    }

    for seat_id in body.seat_ids:
        avail = avail_map.get(seat_id)
        if avail:
            if avail.status == "booked":
                raise HTTPException(status_code=409, detail=f"Seat {seat_id} is already booked")
            if avail.status == "locked" and avail.locked_by != current_user.id:
                raise HTTPException(
                    status_code=409, detail=f"Seat {seat_id} is locked by another user"
                )

    # Lock seats (create or update SeatAvailability records)
    for seat_id in body.seat_ids:
        avail = avail_map.get(seat_id)
        if avail:
            avail.status = "locked"
            avail.locked_by = current_user.id
            avail.locked_until = expires_at
        else:
            db.add(SeatAvailability(
                time_slot_id=slot_id,
                seat_id=seat_id,
                status="locked",
                locked_by=current_user.id,
                locked_until=expires_at,
            ))

    db.commit()

    return SeatLockResponse(
        locked_seats=body.seat_ids,
        locked_until=expires_at,
        ttl_seconds=SEAT_LOCK_MINUTES * 60,
    )


@slot_public_router.delete(
    "/{slot_id}/seats/lock",
    response_model=SeatLockReleaseResponse,
)
def release_seat_locks(
    slot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Release all seat locks held by the current user for this time slot."""
    locked = db.query(SeatAvailability).filter(
        SeatAvailability.time_slot_id == slot_id,
        SeatAvailability.locked_by == current_user.id,
        SeatAvailability.status == "locked",
    ).all()

    released_ids = [a.seat_id for a in locked]
    for a in locked:
        a.status = "available"
        a.locked_by = None
        a.locked_until = None

    db.commit()
    return SeatLockReleaseResponse(released_seats=released_ids)


# ---------------------------------------------------------------------------
# Capacity Hold — for non-seated venues (restaurants, general admission)
# ---------------------------------------------------------------------------


@slot_public_router.post(
    "/{slot_id}/hold",
    response_model=HoldResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hold(
    slot_id: UUID,
    body: HoldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Place a temporary capacity hold for a non-seated venue.
    Hold expires in 10 minutes. Confirms the user's intent before payment.
    """
    slot = db.query(TimeSlot).filter(TimeSlot.id == slot_id, TimeSlot.is_active == True).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=HOLD_MINUTES)

    # Clean up expired holds for this slot
    db.query(BookingHold).filter(
        BookingHold.time_slot_id == slot_id,
        BookingHold.expires_at < now,
    ).delete(synchronize_session="fetch")

    # Available capacity = total - booked - active holds
    active_holds_qty = (
        db.query(sqlfunc.sum(BookingHold.quantity))
        .filter(
            BookingHold.time_slot_id == slot_id,
            BookingHold.expires_at >= now,
        )
        .scalar()
    ) or 0

    remaining = slot.capacity - slot.booked_count - int(active_holds_qty)
    if body.quantity > remaining:
        raise HTTPException(
            status_code=409,
            detail=f"Only {remaining} spot(s) available, requested {body.quantity}",
        )

    hold = BookingHold(
        user_id=current_user.id,
        time_slot_id=slot_id,
        quantity=body.quantity,
        expires_at=expires_at,
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)

    return HoldResponse(
        hold_id=hold.id,
        time_slot_id=slot_id,
        quantity=body.quantity,
        expires_at=expires_at,
        ttl_seconds=HOLD_MINUTES * 60,
        remaining_capacity=remaining - body.quantity,
    )


@slot_public_router.delete(
    "/{slot_id}/hold/{hold_id}",
    response_model=HoldReleaseResponse,
)
def release_hold(
    slot_id: UUID,
    hold_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Release a capacity hold (e.g. user goes back / cancels checkout)."""
    hold = db.query(BookingHold).filter(
        BookingHold.id == hold_id,
        BookingHold.time_slot_id == slot_id,
        BookingHold.user_id == current_user.id,
    ).first()
    if not hold:
        raise HTTPException(status_code=404, detail="Hold not found")

    qty = hold.quantity
    db.delete(hold)
    db.commit()

    return HoldReleaseResponse(released_quantity=qty, time_slot_id=slot_id)
