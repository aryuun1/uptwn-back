from datetime import datetime

from sqlalchemy import and_, or_, exists, not_
from sqlalchemy.orm import Session

from app.models.time_slot import TimeSlot
from app.models.listing import Listing
from app.models.title import Title, CategoryType


def deactivate_past_slots(db: Session) -> int:
    """
    Mark as inactive all time slots whose start date+time has already passed.

    A slot is considered past when:
      - slot_date  < today                              (entire day is gone), or
      - slot_date == today  AND  start_time < now.time (already started today)

    Returns the number of slots deactivated.
    """
    # Use local time — slot_date/start_time are stored as timezone-naive local values
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    count = (
        db.query(TimeSlot)
        .filter(
            TimeSlot.is_active == True,
            or_(
                TimeSlot.slot_date < today,
                and_(
                    TimeSlot.slot_date == today,
                    TimeSlot.start_time < current_time,
                ),
            ),
        )
        .update({"is_active": False}, synchronize_session="fetch")
    )
    db.commit()
    return count


def expire_past_event_listings(db: Session) -> int:
    """
    Automatically expire event listings that have no active time slots left.

    Targets only category == 'events' — movies and restaurants are untouched.

    A listing is expired when:
      - It is still marked active
      - It has at least one time slot ever created (not a brand-new empty listing)
      - None of those slots are still active (deactivate_past_slots already ran)

    Returns the number of listings expired.
    """
    # Subquery: listing has at least one slot (ever created)
    has_any_slot = exists().where(TimeSlot.listing_id == Listing.id)

    # Subquery: listing has at least one slot still active
    has_active_slot = exists().where(
        and_(
            TimeSlot.listing_id == Listing.id,
            TimeSlot.is_active == True,  # noqa: E712
        )
    )

    stale = (
        db.query(Listing)
        .join(Title, Title.id == Listing.title_id)
        .filter(
            Listing.status == "active",
            Title.category == CategoryType.events,
            Title.is_active == True,  # noqa: E712
            has_any_slot,
            ~has_active_slot,
        )
        .all()
    )

    if not stale:
        return 0

    for listing in stale:
        listing.status = "expired"

    db.commit()
    return len(stale)
