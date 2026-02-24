from uuid import UUID
from typing import List, Optional
from datetime import date, datetime, timedelta, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.listing import Listing
from app.models.venue import Venue
from app.models.hall import Hall
from app.models.title import Title, CategoryType
from app.models.time_slot import TimeSlot
from app.schemas.time_slot import (
    TimeSlotCreate,
    TimeSlotUpdate,
    TimeSlotWithHall as TimeSlotSchema,
    BulkTimeSlotCreate,
    BulkCreateResult,
    HallScheduleEntry,
    HallScheduleResponse,
)

router = APIRouter(prefix="/admin/listings", tags=["Admin - Time Slots"])
slot_router = APIRouter(prefix="/admin/time-slots", tags=["Admin - Time Slots"])
hall_schedule_router = APIRouter(prefix="/admin/halls", tags=["Admin - Hall Schedule"])
venue_schedule_router = APIRouter(prefix="/admin/venues", tags=["Admin - Venue Schedule"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_hall_overlap(
    db: Session,
    hall_id: UUID,
    slot_date: date,
    start_time,
    end_time,
    exclude_slot_id: UUID | None = None,
):
    """Raise 409 if the hall already has an overlapping active time slot."""
    if not hall_id:
        return

    from sqlalchemy import or_

    filters = [
        TimeSlot.hall_id == hall_id,
        TimeSlot.slot_date == slot_date,
        TimeSlot.is_active == True,
        TimeSlot.start_time < end_time,
        # end_time can be NULL — treat NULL as "open-ended" (always overlaps)
        or_(TimeSlot.end_time == None, TimeSlot.end_time > start_time),
    ]

    if exclude_slot_id:
        filters.append(TimeSlot.id != exclude_slot_id)

    conflict = db.query(TimeSlot).filter(*filters).first()
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Hall is already occupied from {conflict.start_time} to {conflict.end_time} "
                f"on {conflict.slot_date} (slot {conflict.id})"
            ),
        )


def _check_not_in_past(slot_date: date, start_time: time) -> None:
    """Raise 400 if the slot's date+time is in the past."""
    now = datetime.now()
    slot_dt = datetime.combine(slot_date, start_time)
    if slot_dt < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot create a time slot in the past "
                f"({slot_date} {start_time} is before current time)."
            ),
        )


# ---------------------------------------------------------------------------
# Hall schedule — see what's booked in a hall on a given date
# ---------------------------------------------------------------------------


@hall_schedule_router.get("/{hall_id}/schedule")
def get_hall_schedule(
    hall_id: UUID,
    date: Optional[date] = Query(None, description="Filter by date (omit to see all upcoming)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Show all movies / events scheduled in a specific hall.
    - Pass `date` to see a single day.
    - Omit `date` to see all upcoming slots (today onwards).
    """
    hall = db.query(Hall).filter(Hall.id == hall_id, Hall.is_active == True).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Hall not found")

    from app.api.v1.admin.titles import _expire_stale_listings
    _expire_stale_listings(db)

    query = (
        db.query(TimeSlot, Title.title)
        .join(Listing, Listing.id == TimeSlot.listing_id)
        .join(Title, Title.id == Listing.title_id)
        .filter(
            TimeSlot.hall_id == hall_id,
            TimeSlot.is_active == True,
        )
    )

    if date:
        query = query.filter(TimeSlot.slot_date == date)
    else:
        today = datetime.now(timezone.utc).date()
        query = query.filter(TimeSlot.slot_date >= today)

    slots = query.order_by(TimeSlot.slot_date.desc(), TimeSlot.start_time.desc()).all()

    entries = []
    for slot, title_name in slots:
        entries.append(
            {
                "id": str(slot.id),
                "listing_id": str(slot.listing_id),
                "title_name": title_name,
                "slot_date": str(slot.slot_date),
                "start_time": str(slot.start_time),
                "end_time": str(slot.end_time) if slot.end_time else None,
                "capacity": slot.capacity,
                "booked_count": slot.booked_count,
            }
        )

    return {
        "hall_id": str(hall_id),
        "hall_name": hall.name,
        "screen_type": hall.screen_type,
        "capacity": hall.capacity,
        "slots": entries,
    }


@venue_schedule_router.get("/{venue_id}/schedule")
def get_venue_schedule(
    venue_id: UUID,
    date: Optional[date] = Query(None, description="Filter by date (omit to see all upcoming)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Show all halls of a venue with their occupied time slots.
    The admin calls this when creating a listing to see which
    halls and time slots are free.
    """
    venue = db.query(Venue).filter(Venue.id == venue_id, Venue.is_active == True).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    from app.api.v1.admin.titles import _expire_stale_listings
    _expire_stale_listings(db)

    halls = (
        db.query(Hall)
        .filter(Hall.venue_id == venue_id, Hall.is_active == True)
        .all()
    )

    result = []
    for hall in halls:
        query = (
            db.query(TimeSlot, Title.title)
            .join(Listing, Listing.id == TimeSlot.listing_id)
            .join(Title, Title.id == Listing.title_id)
            .filter(
                TimeSlot.hall_id == hall.id,
                TimeSlot.is_active == True,
            )
        )

        if date:
            query = query.filter(TimeSlot.slot_date == date)
        else:
            today = datetime.now(timezone.utc).date()
            query = query.filter(TimeSlot.slot_date >= today)

        slots = query.order_by(TimeSlot.slot_date.desc(), TimeSlot.start_time.desc()).all()

        result.append(
            {
                "hall_id": str(hall.id),
                "hall_name": hall.name,
                "screen_type": hall.screen_type,
                "capacity": hall.capacity,
                "slots": [
                    {
                        "id": str(slot.id),
                        "listing_id": str(slot.listing_id),
                        "title_name": title_name,
                        "slot_date": str(slot.slot_date),
                        "start_time": str(slot.start_time),
                        "end_time": str(slot.end_time) if slot.end_time else None,
                        "capacity": slot.capacity,
                        "booked_count": slot.booked_count,
                    }
                    for slot, title_name in slots
                ],
            }
        )

    return {
        "venue_id": str(venue_id),
        "venue_name": venue.name,
        "halls": result,
    }


# ---------------------------------------------------------------------------
# Time Slot CRUD (nested under listings for create/list)
# ---------------------------------------------------------------------------


@router.post(
    "/{listing_id}/time-slots",
    response_model=List[TimeSlotSchema],
    status_code=status.HTTP_201_CREATED,
)
def create_time_slots(
    listing_id: UUID,
    data: List[TimeSlotCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    listing = (
        db.query(Listing)
        .join(Title, Title.id == Listing.title_id)
        .filter(Listing.id == listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.title.category == CategoryType.restaurants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Date-specific time slots cannot be created for restaurant listings. "
                "Use POST /admin/listings/{listing_id}/restaurant-slots to create "
                "reusable (date-less) slots instead — a handful of rows covers every "
                "future date without any DB bloat."
            ),
        )

    created = []
    for slot_data in data:
        # Reject past date/time
        _check_not_in_past(slot_data.slot_date, slot_data.start_time)

        # Validate hall belongs to the listing's venue
        if slot_data.hall_id:
            hall = (
                db.query(Hall)
                .filter(
                    Hall.id == slot_data.hall_id,
                    Hall.venue_id == listing.venue_id,
                    Hall.is_active == True,
                )
                .first()
            )
            if not hall:
                raise HTTPException(
                    status_code=404,
                    detail=f"Hall {slot_data.hall_id} not found in this venue",
                )

            # Check for overlapping slots in the same hall
            _check_hall_overlap(
                db,
                hall_id=slot_data.hall_id,
                slot_date=slot_data.slot_date,
                start_time=slot_data.start_time,
                end_time=slot_data.end_time,
            )

        slot = TimeSlot(listing_id=listing_id, **slot_data.model_dump())
        db.add(slot)
        created.append(slot)

    db.commit()
    for s in created:
        db.refresh(s)
    return created


_DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@router.post(
    "/{listing_id}/time-slots/bulk",
    response_model=BulkCreateResult,
    status_code=status.HTTP_201_CREATED,
)
def create_bulk_time_slots(
    listing_id: UUID,
    data: BulkTimeSlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Generate time slots across a date range in one shot.
    Works for all categories — movies, events, restaurants.
    Past dates and already-existing slots are silently skipped.
    """
    listing = (
        db.query(Listing)
        .join(Title, Title.id == Listing.title_id)
        .filter(Listing.id == listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.title.category == CategoryType.restaurants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Bulk date-specific slot creation is not allowed for restaurant listings. "
                "Use POST /admin/listings/{listing_id}/restaurant-slots to create "
                "reusable (date-less) slots — a single set of ~10 rows covers every "
                "future date without creating hundreds of rows per listing."
            ),
        )

    if data.date_from > data.date_to:
        raise HTTPException(status_code=400, detail="date_from must be before or equal to date_to")

    target_weekdays = set()
    for d in data.days:
        wday = _DAY_MAP.get(d.lower())
        if wday is None:
            raise HTTPException(status_code=400, detail=f"Invalid day '{d}'. Use: mon tue wed thu fri sat sun")
        target_weekdays.add(wday)

    # Pre-validate all halls once (not per-date)
    validated_halls = {}
    for slot_def in data.slots:
        if slot_def.hall_id and slot_def.hall_id not in validated_halls:
            hall = db.query(Hall).filter(
                Hall.id == slot_def.hall_id,
                Hall.venue_id == listing.venue_id,
                Hall.is_active == True,  # noqa: E712
            ).first()
            if not hall:
                raise HTTPException(
                    status_code=404,
                    detail=f"Hall {slot_def.hall_id} not found in this venue",
                )
            validated_halls[slot_def.hall_id] = hall

    created_count = 0
    skipped_count = 0
    now = datetime.now()

    current_date = data.date_from
    while current_date <= data.date_to:
        if current_date.weekday() in target_weekdays:
            for slot_def in data.slots:
                # Skip past slots silently
                if datetime.combine(current_date, slot_def.start_time) < now:
                    skipped_count += 1
                    continue

                # Skip if an active slot already exists for this listing/date/start_time
                exists = db.query(TimeSlot).filter(
                    TimeSlot.listing_id == listing_id,
                    TimeSlot.slot_date == current_date,
                    TimeSlot.start_time == slot_def.start_time,
                    TimeSlot.is_active == True,  # noqa: E712
                ).first()
                if exists:
                    skipped_count += 1
                    continue

                # Hall overlap check (movies/events only)
                if slot_def.hall_id:
                    _check_hall_overlap(
                        db,
                        hall_id=slot_def.hall_id,
                        slot_date=current_date,
                        start_time=slot_def.start_time,
                        end_time=slot_def.end_time,
                    )

                db.add(TimeSlot(
                    listing_id=listing_id,
                    hall_id=slot_def.hall_id,
                    slot_date=current_date,
                    start_time=slot_def.start_time,
                    end_time=slot_def.end_time,
                    capacity=slot_def.capacity,
                    price_override=slot_def.price_override,
                    slot_type=slot_def.slot_type,
                    discount_percent=slot_def.discount_percent,
                ))
                created_count += 1

        current_date += timedelta(days=1)

    db.commit()
    return BulkCreateResult(created=created_count, skipped=skipped_count)


@router.get(
    "/{listing_id}/time-slots",
    response_model=List[TimeSlotSchema],
)
def list_time_slots(
    listing_id: UUID,
    date: Optional[date] = None,
    hall_id: Optional[UUID] = None,
    show_past: bool = Query(False, description="Include expired/past time slots (is_active=False)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    query = db.query(TimeSlot).filter(TimeSlot.listing_id == listing_id)

    if not show_past:
        query = query.filter(TimeSlot.is_active == True)
    else:
        # Past slots only — no point returning future active ones in history view
        query = query.filter(TimeSlot.is_active == False)

    if date:
        query = query.filter(TimeSlot.slot_date == date)
    if hall_id:
        query = query.filter(TimeSlot.hall_id == hall_id)

    return query.order_by(TimeSlot.slot_date.desc(), TimeSlot.start_time.desc()).all()


# ---------------------------------------------------------------------------
# Flat time slot update/delete
# ---------------------------------------------------------------------------


@slot_router.patch("/{id}", response_model=TimeSlotSchema)
def update_time_slot(
    id: UUID,
    data: TimeSlotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    slot = db.query(TimeSlot).filter(TimeSlot.id == id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")

    updates = data.model_dump(exclude_unset=True)

    # If hall, date, or times are changing, check for overlap with new values
    new_hall = updates.get("hall_id", slot.hall_id)
    new_date = updates.get("slot_date", slot.slot_date)
    new_start = updates.get("start_time", slot.start_time)
    new_end = updates.get("end_time", slot.end_time)

    if new_hall:
        _check_hall_overlap(
            db,
            hall_id=new_hall,
            slot_date=new_date,
            start_time=new_start,
            end_time=new_end,
            exclude_slot_id=id,
        )

    for field, value in updates.items():
        setattr(slot, field, value)

    db.commit()
    db.refresh(slot)
    return slot


@slot_router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_time_slot(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    slot = db.query(TimeSlot).filter(TimeSlot.id == id, TimeSlot.is_active == True).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Time slot not found")

    slot.is_active = False
    db.commit()
    return {"id": str(id), "is_active": False}
