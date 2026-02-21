from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.time_slot import TimeSlot


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
