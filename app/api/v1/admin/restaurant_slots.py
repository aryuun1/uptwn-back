from uuid import UUID
from datetime import date, datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.listing import Listing
from app.models.time_slot import TimeSlot
from app.models.booking import Booking
from app.models.title import Title, CategoryType
from app.schemas.restaurant import RestaurantSlotCreate, RestaurantSlotAdmin

# Two routers so we can mount them under different prefixes in router.py
listing_router = APIRouter(prefix="/admin/listings", tags=["Admin - Restaurant Slots"])
slot_router = APIRouter(prefix="/admin/restaurant-slots", tags=["Admin - Restaurant Slots"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_restaurant_listing(listing_id: UUID, db: Session) -> Listing:
    """Fetch a listing and verify it belongs to a restaurant title."""
    listing = (
        db.query(Listing)
        .join(Title, Title.id == Listing.title_id)
        .filter(
            Listing.id == listing_id,
            Title.category == CategoryType.restaurants,
        )
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Restaurant listing not found")
    return listing


# ---------------------------------------------------------------------------
# POST /admin/listings/{listing_id}/restaurant-slots
# ---------------------------------------------------------------------------


@listing_router.post(
    "/{listing_id}/restaurant-slots",
    response_model=List[RestaurantSlotAdmin],
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant_slots(
    listing_id: UUID,
    data: List[RestaurantSlotCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Create reusable (date-less) time slots for a restaurant listing.

    Each row represents a recurring time window — e.g. "Lunch 12:00-14:30" or
    "Dinner 19:00-22:00". A restaurant typically needs only 5-10 of these rows
    total, and they cover every future date forever.

    At booking time the user supplies the date; availability is computed live by
    counting confirmed bookings + active holds for that slot on that date.

    Duplicate slot_type + start_time combinations for the same listing are rejected.
    """
    _get_restaurant_listing(listing_id, db)

    # Collect existing active keys to prevent duplicates within this batch too
    existing = (
        db.query(TimeSlot)
        .filter(
            TimeSlot.listing_id == listing_id,
            TimeSlot.slot_date == None,   # noqa: E711
            TimeSlot.is_active == True,   # noqa: E712
        )
        .all()
    )
    seen_keys = {(s.slot_type, str(s.start_time)) for s in existing}

    created = []
    for slot_data in data:
        key = (slot_data.slot_type, str(slot_data.start_time))
        if key in seen_keys:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"An active '{slot_data.slot_type}' slot starting at "
                    f"{slot_data.start_time} already exists for this listing."
                ),
            )
        seen_keys.add(key)

        slot = TimeSlot(
            listing_id=listing_id,
            slot_date=None,
            start_time=slot_data.start_time,
            end_time=slot_data.end_time,
            capacity=slot_data.capacity,
            slot_type=slot_data.slot_type,
            discount_percent=slot_data.discount_percent,
        )
        db.add(slot)
        created.append(slot)

    db.commit()
    for s in created:
        db.refresh(s)
    return created


# ---------------------------------------------------------------------------
# GET /admin/listings/{listing_id}/restaurant-slots
# ---------------------------------------------------------------------------


@listing_router.get(
    "/{listing_id}/restaurant-slots",
    response_model=List[RestaurantSlotAdmin],
)
def list_restaurant_slots(
    listing_id: UUID,
    include_inactive: bool = Query(False, description="Also return deactivated slots"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    List all reusable template slots for a restaurant listing (admin view).
    By default only active slots are returned; pass include_inactive=true for all.
    """
    _get_restaurant_listing(listing_id, db)

    query = db.query(TimeSlot).filter(
        TimeSlot.listing_id == listing_id,
        TimeSlot.slot_date == None,   # noqa: E711
    )
    if not include_inactive:
        query = query.filter(TimeSlot.is_active == True)   # noqa: E712

    return query.order_by(TimeSlot.slot_type, TimeSlot.start_time).all()


# ---------------------------------------------------------------------------
# DELETE /admin/restaurant-slots/purge-past
# ---------------------------------------------------------------------------


@slot_router.delete(
    "/purge-past",
    status_code=status.HTTP_200_OK,
)
def purge_past_restaurant_timeslots(
    before_date: date = Query(
        None,
        description="Delete date-specific slots strictly before this date (default: today)",
    ),
    dry_run: bool = Query(False, description="Preview counts only — no deletion"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Hard-delete past date-specific time slots that belong to restaurant listings.

    These rows are legacy data from before the guard was added — restaurants should
    only use reusable (slot_date = NULL) slots going forward, so date-specific rows
    are safe to remove once their date has passed.

    **What is deleted:**
    - TimeSlot rows where listing → title.category = 'restaurants'
      AND slot_date IS NOT NULL AND slot_date < cutoff

    **What is preserved:**
    - Booking records — time_slot_id is nulled out (it is nullable) before deletion.
      event_date is already stored directly on each Booking row so history is intact.
    - BookingHold rows cascade-delete automatically with their parent slot.
    - Reusable slots (slot_date = NULL) are never touched.

    Pass dry_run=true to see what would be affected without committing anything.
    """
    cutoff = before_date or datetime.now(timezone.utc).date()

    past_slots = (
        db.query(TimeSlot)
        .join(Listing, Listing.id == TimeSlot.listing_id)
        .join(Title, Title.id == Listing.title_id)
        .filter(
            Title.category == CategoryType.restaurants,
            TimeSlot.slot_date != None,   # noqa: E711 — reusable slots are exempt
            TimeSlot.slot_date < cutoff,
        )
        .all()
    )

    if not past_slots:
        return {
            "dry_run": dry_run,
            "deleted": 0,
            "bookings_unlinked": 0,
            "message": "No past date-specific restaurant slots found.",
        }

    slot_ids = [s.id for s in past_slots]

    affected_bookings = (
        db.query(Booking)
        .filter(Booking.time_slot_id.in_(slot_ids))
        .count()
    )

    if dry_run:
        return {
            "dry_run": True,
            "would_delete": len(slot_ids),
            "bookings_to_unlink": affected_bookings,
            "cutoff_date": str(cutoff),
        }

    # Preserve bookings — unlink the slot reference before deleting the slot.
    # The booking still has listing_id, event_date, party_size, booking_number etc.
    if affected_bookings:
        db.query(Booking).filter(Booking.time_slot_id.in_(slot_ids)).update(
            {"time_slot_id": None}, synchronize_session=False
        )

    # Hard-delete. BookingHold rows cascade via the relationship on TimeSlot.
    for slot in past_slots:
        db.delete(slot)

    db.commit()

    return {
        "dry_run": False,
        "deleted": len(slot_ids),
        "bookings_unlinked": affected_bookings,
        "cutoff_date": str(cutoff),
    }
