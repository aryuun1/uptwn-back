import random
import string
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.booking import Booking, BookingSeat, BookingHold
from app.models.listing import Listing
from app.models.time_slot import TimeSlot
from app.models.seat import Seat, SeatAvailability
from app.models.review_notification import Notification
from app.schemas.booking import (
    BookingCreate,
    Booking as BookingSchema,
    BookingCancelResponse,
    BookingListingSummary,
    BookingVenueSummary,
    BookingTimeSlotSummary,
    BookingSeatResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_booking_number(db: Session) -> str:
    """Generate a unique 'UPT-XXXXXXXX' booking reference."""
    chars = string.ascii_uppercase + string.digits
    while True:
        number = "UPT-" + "".join(random.choices(chars, k=8))
        if not db.query(Booking).filter(Booking.booking_number == number).first():
            return number


def _load_booking(booking_id: UUID, user_id, db: Session) -> Booking:
    """Load a booking with all relations eager-loaded."""
    booking = (
        db.query(Booking)
        .options(
            joinedload(Booking.listing).joinedload(Listing.title),
            joinedload(Booking.listing).joinedload(Listing.venue),
            joinedload(Booking.time_slot).joinedload(TimeSlot.hall),
            joinedload(Booking.seats).joinedload(BookingSeat.seat),
        )
        .filter(Booking.id == booking_id, Booking.user_id == user_id)
        .first()
    )
    return booking


def _serialize_booking(booking: Booking) -> BookingSchema:
    """Convert a Booking ORM object to its schema representation."""
    listing_summary = None
    venue_summary = None
    if booking.listing:
        t = booking.listing.title
        listing_summary = BookingListingSummary(
            title=t.title if t else "",
            image_url=t.image_url if t else None,
            category=t.category if t else None,
        )
        v = booking.listing.venue
        if v:
            venue_summary = BookingVenueSummary(name=v.name, city=v.city)

    slot_summary = None
    if booking.time_slot:
        ts = booking.time_slot
        slot_summary = BookingTimeSlotSummary(
            slot_date=ts.slot_date,
            start_time=str(ts.start_time),
            end_time=str(ts.end_time) if ts.end_time else None,
            hall_id=ts.hall_id,
            hall_name=ts.hall.name if ts.hall else None,
        )

    seats_out = [
        BookingSeatResponse(
            row=bs.seat.row_label,
            number=bs.seat.seat_number,
            category=bs.seat.category,
            price=bs.seat.price,
        )
        for bs in booking.seats
    ]

    return BookingSchema(
        id=booking.id,
        booking_number=booking.booking_number,
        listing_id=booking.listing_id,
        time_slot_id=booking.time_slot_id,
        quantity=booking.quantity,
        total_amount=booking.total_amount,
        status=booking.status,
        booking_date=booking.booking_date,
        event_date=booking.event_date,
        notes=booking.notes,
        cancelled_at=booking.cancelled_at,
        created_at=booking.created_at,
        listing=listing_summary,
        venue=venue_summary,
        time_slot=slot_summary,
        seats=seats_out,
    )


# ---------------------------------------------------------------------------
# POST /bookings — create / confirm a booking
# ---------------------------------------------------------------------------


@router.post("/", response_model=BookingSchema, status_code=status.HTTP_201_CREATED)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Confirm a booking. Two flows:

    **Seat-based** (cinemas, stadiums):
    - Provide `time_slot_id` + `seat_ids`.
    - All seats must be locked by the current user.
    - Total is summed from individual seat prices.

    **Capacity-based** (restaurants, general admission):
    - Provide `listing_id`, optionally `time_slot_id` and `quantity`.
    - Total = unit price × quantity.
    - Any active hold for this user + slot is released automatically.
    """
    # Load listing with relations
    listing = (
        db.query(Listing)
        .options(joinedload(Listing.title), joinedload(Listing.venue))
        .filter(Listing.id == data.listing_id, Listing.status == "active")
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or inactive")

    # Load time slot if provided
    slot: Optional[TimeSlot] = None
    if data.time_slot_id:
        slot = db.query(TimeSlot).filter(
            TimeSlot.id == data.time_slot_id,
            TimeSlot.listing_id == data.listing_id,
            TimeSlot.is_active == True,
        ).first()
        if not slot:
            raise HTTPException(status_code=404, detail="Time slot not found or inactive")

    now = datetime.now(timezone.utc)

    # -----------------------------------------------------------------------
    # Seat-based booking
    # -----------------------------------------------------------------------
    if data.seat_ids:
        if not slot:
            raise HTTPException(
                status_code=400,
                detail="time_slot_id is required when booking specific seats",
            )

        seat_ids = list(data.seat_ids)
        quantity = len(seat_ids)

        # All seats must be locked by this user and not expired
        locked_avails = db.query(SeatAvailability).filter(
            SeatAvailability.time_slot_id == slot.id,
            SeatAvailability.seat_id.in_(seat_ids),
            SeatAvailability.status == "locked",
            SeatAvailability.locked_by == current_user.id,
            SeatAvailability.locked_until >= now,
        ).all()

        if len(locked_avails) != quantity:
            raise HTTPException(
                status_code=409,
                detail="One or more seats are not locked by you, or the lock has expired",
            )

        # Capacity check
        if slot.booked_count + quantity > slot.capacity:
            raise HTTPException(status_code=409, detail="Time slot is at full capacity")

        # Compute total: slot override → listing price → individual seat prices
        unit_price = (
            slot.price_override if slot.price_override else None
        ) or listing.price
        if unit_price is not None:
            total_amount = float(unit_price) * quantity
        else:
            seats = db.query(Seat).filter(Seat.id.in_(seat_ids)).all()
            total_amount = sum(float(s.price) for s in seats)

        booking_number = _generate_booking_number(db)
        booking = Booking(
            user_id=current_user.id,
            listing_id=listing.id,
            time_slot_id=slot.id,
            booking_number=booking_number,
            quantity=quantity,
            total_amount=total_amount,
            status="confirmed",
            event_date=slot.slot_date,
            notes=data.notes,
        )
        db.add(booking)
        db.flush()  # get booking.id

        # Commit seats → booked and create BookingSeat join records
        for avail in locked_avails:
            db.add(BookingSeat(
                booking_id=booking.id,
                seat_id=avail.seat_id,
                time_slot_id=slot.id,
            ))
            avail.status = "booked"
            avail.locked_by = None
            avail.locked_until = None

        slot.booked_count += quantity
        listing.booked_count += quantity

    # -----------------------------------------------------------------------
    # Capacity-based booking (no specific seats)
    # -----------------------------------------------------------------------
    else:
        quantity = data.quantity

        # Determine unit price: slot override → listing price → 0
        unit_price = float(
            (slot.price_override if slot and slot.price_override else None)
            or listing.price
            or 0
        )
        total_amount = unit_price * quantity

        # Capacity check
        if slot:
            if slot.booked_count + quantity > slot.capacity:
                raise HTTPException(status_code=409, detail="Not enough capacity in this slot")
        elif listing.total_capacity is not None:
            if listing.booked_count + quantity > listing.total_capacity:
                raise HTTPException(status_code=409, detail="Listing is fully booked")

        event_date = data.event_date or (slot.slot_date if slot else None)
        booking_number = _generate_booking_number(db)
        booking = Booking(
            user_id=current_user.id,
            listing_id=listing.id,
            time_slot_id=slot.id if slot else None,
            booking_number=booking_number,
            quantity=quantity,
            total_amount=total_amount,
            status="confirmed",
            event_date=event_date,
            notes=data.notes,
        )
        db.add(booking)
        db.flush()

        if slot:
            slot.booked_count += quantity
        listing.booked_count += quantity

        # Release any capacity holds for this user + slot
        if slot:
            db.query(BookingHold).filter(
                BookingHold.user_id == current_user.id,
                BookingHold.time_slot_id == slot.id,
            ).delete(synchronize_session="fetch")

    # Booking confirmation notification
    title_name = listing.title.title if listing.title else "your experience"
    db.add(Notification(
        user_id=current_user.id,
        title="Booking Confirmed",
        message=(
            f"Your booking for {title_name} is confirmed! "
            f"Ref: {booking.booking_number}"
        ),
        type="booking_confirmed",
        reference_id=booking.id,
    ))

    db.commit()

    # Reload fully for response
    full_booking = _load_booking(booking.id, current_user.id, db)
    return _serialize_booking(full_booking)


# ---------------------------------------------------------------------------
# GET /bookings — list current user's bookings
# ---------------------------------------------------------------------------


@router.get("/", response_model=PaginatedResponse[BookingSchema])
def list_my_bookings(
    status: Optional[str] = Query(
        None, description="Filter by status: confirmed, cancelled, completed, pending"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's bookings, newest first."""
    query = (
        db.query(Booking)
        .options(
            joinedload(Booking.listing).joinedload(Listing.title),
            joinedload(Booking.listing).joinedload(Listing.venue),
            joinedload(Booking.time_slot).joinedload(TimeSlot.hall),
            joinedload(Booking.seats).joinedload(BookingSeat.seat),
        )
        .filter(Booking.user_id == current_user.id)
    )
    if status:
        query = query.filter(Booking.status == status)

    total = query.count()
    bookings = (
        query.order_by(Booking.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        data=[_serialize_booking(b) for b in bookings],
        total=total,
        page=page,
        limit=limit,
        total_pages=-(-total // limit) if total else 0,
    )


# ---------------------------------------------------------------------------
# GET /bookings/{id} — single booking detail
# ---------------------------------------------------------------------------


@router.get("/{booking_id}", response_model=BookingSchema)
def get_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a single booking. Only the owning user can access it."""
    booking = _load_booking(booking_id, current_user.id, db)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _serialize_booking(booking)


# ---------------------------------------------------------------------------
# PATCH /bookings/{id}/cancel
# ---------------------------------------------------------------------------


@router.patch("/{booking_id}/cancel", response_model=BookingCancelResponse)
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a confirmed booking.
    - Frees time slot and listing capacity.
    - Releases seat availability back to 'available'.
    - Sends a cancellation notification.
    """
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == current_user.id,
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "confirmed":
        raise HTTPException(
            status_code=409,
            detail=f"Only confirmed bookings can be cancelled (current status: '{booking.status}')",
        )

    now = datetime.now(timezone.utc)
    booking.status = "cancelled"
    booking.cancelled_at = now

    # Free time slot capacity
    if booking.time_slot_id:
        slot = db.query(TimeSlot).filter(TimeSlot.id == booking.time_slot_id).first()
        if slot:
            slot.booked_count = max(0, slot.booked_count - booking.quantity)

    # Free listing capacity
    listing = db.query(Listing).filter(Listing.id == booking.listing_id).first()
    if listing:
        listing.booked_count = max(0, listing.booked_count - booking.quantity)

    # Release seat availability
    seat_ids = [bs.seat_id for bs in booking.seats]
    if seat_ids:
        db.query(SeatAvailability).filter(
            SeatAvailability.time_slot_id == booking.time_slot_id,
            SeatAvailability.seat_id.in_(seat_ids),
        ).update(
            {"status": "available", "locked_by": None, "locked_until": None},
            synchronize_session="fetch",
        )

    # Cancellation notification
    db.add(Notification(
        user_id=current_user.id,
        title="Booking Cancelled",
        message=f"Your booking #{booking.booking_number} has been cancelled.",
        type="cancelled",
        reference_id=booking.id,
    ))

    db.commit()
    db.refresh(booking)

    return BookingCancelResponse(
        id=booking.id,
        booking_number=booking.booking_number,
        status=booking.status,
        cancelled_at=booking.cancelled_at,
    )
