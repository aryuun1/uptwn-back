from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.booking import Booking, BookingSeat
from app.models.listing import Listing
from app.models.time_slot import TimeSlot
from app.models.title import Title
from app.schemas.booking import (
    AdminBooking,
    BookingListingSummary,
    BookingVenueSummary,
    BookingTimeSlotSummary,
    BookingSeatResponse,
)
from app.schemas.user import UserSummary
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/admin/bookings", tags=["Admin - Bookings"])


def _serialize_admin_booking(booking: Booking) -> AdminBooking:
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

    user_summary = None
    if booking.user:
        user_summary = UserSummary(
            id=booking.user.id,
            full_name=booking.user.full_name,
            email=booking.user.email,
        )

    return AdminBooking(
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
        user=user_summary,
    )


@router.get("/", response_model=PaginatedResponse[AdminBooking])
def list_all_bookings(
    # --- Filters ---
    category: Optional[str] = Query(None, description="Filter by title category (movies, events, restaurants)"),
    slug: Optional[str] = Query(None, description="Filter by title slug"),
    date: Optional[date] = Query(None, description="Filter by event date (YYYY-MM-DD)"),
    city: Optional[str] = Query(None, description="Filter by city (case-insensitive)"),
    status: Optional[str] = Query(None, description="Filter by booking status (confirmed, cancelled, completed, pending)"),
    # --- Pagination ---
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Return all bookings across every listing, time slot, and event.
    Supports filtering by title category, slug, event date, city, and booking status.
    """
    query = (
        db.query(Booking)
        .join(Listing, Listing.id == Booking.listing_id)
        .join(Title, Title.id == Listing.title_id)
        .options(
            joinedload(Booking.user),
            joinedload(Booking.listing).joinedload(Listing.title),
            joinedload(Booking.listing).joinedload(Listing.venue),
            joinedload(Booking.time_slot),
            joinedload(Booking.seats).joinedload(BookingSeat.seat),
        )
    )

    if category:
        query = query.filter(Title.category == category)
    if slug:
        query = query.filter(Title.slug == slug)
    if date:
        query = query.filter(Booking.event_date == date)
    if city:
        query = query.filter(Listing.city.ilike(city))
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
        data=[_serialize_admin_booking(b) for b in bookings],
        total=total,
        page=page,
        limit=limit,
        total_pages=-(-total // limit) if total else 0,
    )
