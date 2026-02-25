import random
import string
from decimal import Decimal
from uuid import UUID
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.listing import Listing
from app.models.time_slot import TimeSlot
from app.models.booking import Booking, BookingHold
from app.schemas.restaurant import (
    RestaurantBookingCreate,
    RestaurantBookingResponse,
    RestaurantSlotGroup,
    RestaurantSlotWindow,
)

router = APIRouter(prefix="/listings", tags=["Restaurant Slots"])
booking_router = APIRouter(prefix="/restaurant-bookings", tags=["Restaurant Bookings"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_booking_number(db: Session) -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        number = "UPT-" + "".join(random.choices(chars, k=8))
        if not db.query(Booking).filter(Booking.booking_number == number).first():
            return number


def _count_taken(db: Session, time_slot_id, event_date: date, now: datetime) -> int:
    """Count confirmed bookings + active holds for a reusable slot on a specific date."""
    booked = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.time_slot_id == time_slot_id,
            Booking.event_date == event_date,
            Booking.status.notin_(["cancelled"]),
        )
        .scalar()
        or 0
    )

    held = (
        db.query(func.count(BookingHold.id))
        .filter(
            BookingHold.time_slot_id == time_slot_id,
            BookingHold.slot_date == event_date,
            BookingHold.expires_at > now,
        )
        .scalar()
        or 0
    )

    return booked + held


# ---------------------------------------------------------------------------
# GET /listings/{listing_id}/restaurant-slots?date=
# ---------------------------------------------------------------------------


@router.get("/{listing_id}/restaurant-slots", response_model=list[RestaurantSlotGroup])
def get_restaurant_slots(
    listing_id: UUID,
    date: date = Query(..., description="Date to check availability (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Return all reusable time slots for a restaurant listing,
    grouped by slot_type (lunch / dinner), with live availability
    computed for the requested date.
    """
    listing = (
        db.query(Listing)
        .filter(Listing.id == listing_id, Listing.status == "active")
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    now = datetime.now(timezone.utc)
    now_local = datetime.now()

    # Reusable slots have slot_date = NULL
    query = (
        db.query(TimeSlot)
        .filter(
            TimeSlot.listing_id == listing_id,
            TimeSlot.slot_date == None,  # noqa: E711
            TimeSlot.is_active == True,  # noqa: E712
        )
    )

    # If the requested date is today, exclude slots whose start_time has already passed
    if date == now_local.date():
        query = query.filter(TimeSlot.start_time > now_local.time())

    slots = query.order_by(TimeSlot.slot_type, TimeSlot.start_time).all()

    # Group by slot_type
    groups: dict[str, list[RestaurantSlotWindow]] = {}
    for slot in slots:
        slot_type = slot.slot_type or "general"
        taken = _count_taken(db, slot.id, date, now)
        available = max(0, slot.capacity - taken)

        window = RestaurantSlotWindow(
            id=slot.id,
            start_time=slot.start_time,
            end_time=slot.end_time,
            slot_type=slot.slot_type,
            discount_percent=slot.discount_percent,
            available=available,
            capacity=slot.capacity,
            is_full=(available == 0),
        )
        groups.setdefault(slot_type, []).append(window)

    return [
        RestaurantSlotGroup(slot_type=st, windows=windows)
        for st, windows in groups.items()
    ]


# ---------------------------------------------------------------------------
# POST /restaurant-bookings
# ---------------------------------------------------------------------------


@booking_router.post(
    "/",
    response_model=RestaurantBookingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant_booking(
    data: RestaurantBookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Book a restaurant slot.

    - **cover**: Pay ₹100 cover charge → confirmed Booking (slot discount applied to estimate).
    - **reserve**: Free reservation → BookingHold (expires at slot end_time on event_date, 10% off estimate).
    """
    listing = (
        db.query(Listing)
        .options(joinedload(Listing.title))
        .filter(Listing.id == data.listing_id, Listing.status == "active")
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or inactive")

    # Must be a reusable (restaurant) slot — slot_date is NULL
    slot = (
        db.query(TimeSlot)
        .filter(
            TimeSlot.id == data.time_slot_id,
            TimeSlot.listing_id == data.listing_id,
            TimeSlot.slot_date == None,  # noqa: E711
            TimeSlot.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")

    if data.party_size < 1:
        raise HTTPException(status_code=400, detail="party_size must be at least 1")
    if data.booking_type not in ("cover", "reserve"):
        raise HTTPException(status_code=400, detail="booking_type must be 'cover' or 'reserve'")

    # Check live availability for the requested date
    now = datetime.now(timezone.utc)
    taken = _count_taken(db, slot.id, data.event_date, now)
    if taken >= slot.capacity:
        raise HTTPException(
            status_code=409,
            detail="This time slot is fully booked for the selected date",
        )

    # Discount and estimate
    slot_discount = float(slot.discount_percent) if slot.discount_percent else 0.0
    if data.booking_type == "cover":
        discount_pct = slot_discount
        cover_charge = Decimal("100.00")
    else:
        discount_pct = 10.0
        cover_charge = Decimal("0.00")

    avg_per_person = float(listing.price) if listing.price else 0.0
    estimate = Decimal(
        str(round(avg_per_person * data.party_size * (1 - discount_pct / 100), 2))
    )

    # -----------------------------------------------------------------------
    # Cover → confirmed Booking
    # -----------------------------------------------------------------------
    if data.booking_type == "cover":
        booking_number = _generate_booking_number(db)
        booking = Booking(
            user_id=current_user.id,
            listing_id=listing.id,
            time_slot_id=slot.id,
            booking_number=booking_number,
            quantity=1,
            total_amount=float(cover_charge),
            status="confirmed",
            event_date=data.event_date,
            notes=data.notes,
            party_size=data.party_size,
            booking_type=data.booking_type,
            cover_charge_paid=cover_charge,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        return RestaurantBookingResponse(
            type="booking",
            id=booking.id,
            listing_id=listing.id,
            time_slot_id=slot.id,
            slot_type=slot.slot_type,
            slot_date=data.event_date,
            start_time=slot.start_time,
            end_time=slot.end_time,
            party_size=data.party_size,
            booking_type=data.booking_type,
            discount_percent=slot.discount_percent,
            cover_charge_paid=cover_charge,
            estimate=estimate,
            status="confirmed",
            booking_number=booking_number,
            expires_at=None,
            created_at=booking.created_at,
        )

    # -----------------------------------------------------------------------
    # Reserve → confirmed Booking with no cover charge
    # -----------------------------------------------------------------------
    booking_number = _generate_booking_number(db)
    booking = Booking(
        user_id=current_user.id,
        listing_id=listing.id,
        time_slot_id=slot.id,
        booking_number=booking_number,
        quantity=1,
        total_amount=0,
        status="confirmed",
        event_date=data.event_date,
        notes=data.notes,
        party_size=data.party_size,
        booking_type=data.booking_type,
        cover_charge_paid=Decimal("0.00"),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return RestaurantBookingResponse(
        type="booking",
        id=booking.id,
        listing_id=listing.id,
        time_slot_id=slot.id,
        slot_type=slot.slot_type,
        slot_date=data.event_date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        party_size=data.party_size,
        booking_type=data.booking_type,
        discount_percent=slot.discount_percent,
        cover_charge_paid=Decimal("0.00"),
        estimate=estimate,
        status="confirmed",
        booking_number=booking_number,
        expires_at=None,
        created_at=booking.created_at,
    )
