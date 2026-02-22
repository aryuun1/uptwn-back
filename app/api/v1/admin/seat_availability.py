
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.seat import SeatAvailability
from app.models.time_slot import TimeSlot

router = APIRouter(prefix="/admin/seat-availability", tags=["Admin - Seat Availability"])


@router.post("/cleanup")
def cleanup_seat_availability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Cleanup utility for seat_availability table.

    Removes two categories of junk rows:

    1. **Stale rows** — any row (booked/locked/available) whose time slot is in
       the past or has been deactivated. Past bookings are already captured in
       the `bookings` / `booking_seats` tables, so these rows are safe to drop.

    2. **Redundant "available" rows** — the seat map already treats a missing row
       as "available", so storing explicit available rows wastes space.

    Going forward, seat_availability only holds `locked` and `booked` rows.
    Available = no row (implicit).
    """
    today = datetime.now(timezone.utc).date()

    # --- Step 1: delete rows for past or inactive time slots (any status) ---
    past_slot_subquery = (
        db.query(TimeSlot.id)
        .filter(
            or_(
                TimeSlot.slot_date < today,
                TimeSlot.is_active == False,
            )
        )
        .scalar_subquery()
    )

    deleted_stale = (
        db.query(SeatAvailability)
        .filter(SeatAvailability.time_slot_id.in_(past_slot_subquery))
        .delete(synchronize_session="fetch")
    )

    # --- Step 2: delete remaining "available" rows (redundant by design) ---
    deleted_redundant = (
        db.query(SeatAvailability)
        .filter(SeatAvailability.status == "available")
        .delete(synchronize_session="fetch")
    )

    db.commit()

    return {
        "deleted_stale_slot_rows": deleted_stale,
        "deleted_redundant_available_rows": deleted_redundant,
        "total_deleted": deleted_stale + deleted_redundant,
        "message": (
            "Cleanup complete. seat_availability now only contains locked/booked rows. "
            "Available seats are implied by the absence of a row."
        ),
    }


@router.get("/stats")
def seat_availability_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Returns a breakdown of seat_availability rows by status and slot recency.
    Useful for monitoring DB health before/after cleanup.
    """
    today = datetime.now(timezone.utc).date()

    total = db.query(SeatAvailability).count()

    available_count = (
        db.query(SeatAvailability)
        .filter(SeatAvailability.status == "available")
        .count()
    )
    locked_count = (
        db.query(SeatAvailability)
        .filter(SeatAvailability.status == "locked")
        .count()
    )
    booked_count = (
        db.query(SeatAvailability)
        .filter(SeatAvailability.status == "booked")
        .count()
    )

    past_slot_subquery = (
        db.query(TimeSlot.id)
        .filter(
            or_(
                TimeSlot.slot_date < today,
                TimeSlot.is_active == False,
            )
        )
        .scalar_subquery()
    )
    stale_count = (
        db.query(SeatAvailability)
        .filter(SeatAvailability.time_slot_id.in_(past_slot_subquery))
        .count()
    )

    return {
        "total_rows": total,
        "by_status": {
            "available": available_count,
            "locked": locked_count,
            "booked": booked_count,
        },
        "stale_past_slot_rows": stale_count,
        "redundant_rows_to_cleanup": stale_count + available_count,
    }
