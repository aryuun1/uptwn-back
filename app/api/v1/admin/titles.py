
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.title import Title, TitleImage, CategoryType
from app.models.listing import Listing
from app.models.venue import Venue
from app.models.time_slot import TimeSlot
from app.models.hall import Hall
from app.schemas.title import (
    TitleCreate,
    TitleUpdate,
    Title as TitleSchema,
    TitleImageCreate,
    TitleImage as TitleImageSchema,
    ListingCreate,
    ListingUpdate,
    Listing as ListingSchema,
)
from app.schemas.time_slot import BulkListingCreate, BulkListingResponse
from app.schemas.common import PaginatedResponse
from app.utils.slug import make_unique_slug

router = APIRouter(prefix="/admin/titles", tags=["Admin - Titles"])
listing_router = APIRouter(prefix="/admin/listings", tags=["Admin - Listings"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _expire_stale_listings(db: Session):
    """
    Mark listings as 'expired' when current date is past their end_datetime,
    and deactivate their time slots to free up hall capacity.
    """
    now = datetime.now(timezone.utc)

    stale_listings = (
        db.query(Listing)
        .filter(
            Listing.status == "active",
            Listing.end_datetime != None,  # noqa: E711
            Listing.end_datetime < now,
        )
        .all()
    )

    if not stale_listings:
        return

    stale_ids = [l.id for l in stale_listings]

    # Deactivate all time slots belonging to expired listings
    db.query(TimeSlot).filter(
        TimeSlot.listing_id.in_(stale_ids),
        TimeSlot.is_active == True,  # noqa: E712
    ).update({"is_active": False}, synchronize_session="fetch")

    # Mark listings as expired
    for listing in stale_listings:
        listing.status = "expired"

    db.commit()


# ---------------------------------------------------------------------------
# Title CRUD
# ---------------------------------------------------------------------------


@router.get("/", response_model=PaginatedResponse[TitleSchema])
def list_titles(
    is_active: Optional[bool] = True,
    category: Optional[CategoryType] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = Query("newest", pattern="^(newest|oldest)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    query = db.query(Title)
    if is_active is not None:
        query = query.filter(Title.is_active == is_active)
    if category:
        query = query.filter(Title.category == category)
    if search:
        query = query.filter(Title.title.ilike(f"%{search}%"))
    if city:
        query = query.filter(
            Title.id.in_(
                db.query(Listing.title_id).filter(Listing.city.ilike(f"%{city}%"))
            )
        )
    order = Title.created_at.asc() if sort == "oldest" else Title.created_at.desc()
    query = query.order_by(order)

    total = query.count()
    titles = query.offset((page - 1) * limit).limit(limit).all()

    return PaginatedResponse(
        data=titles,
        total=total,
        page=page,
        limit=limit,
        total_pages=-(-total // limit) if total else 0,
    )


@router.get("/{id}", response_model=TitleSchema)
def get_title(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    title = db.query(Title).filter(Title.id == id).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")
    return title


@router.post("/", response_model=TitleSchema, status_code=status.HTTP_201_CREATED)
def create_title(
    data: TitleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    slug = make_unique_slug(db, data.title)
    title = Title(
        slug=slug,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(title)
    db.commit()
    db.refresh(title)
    return title


@router.patch("/{id}", response_model=TitleSchema)
def update_title(
    id: UUID,
    data: TitleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    title = db.query(Title).filter(Title.id == id).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(title, field, value)

    db.commit()
    db.refresh(title)
    return title


@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_title(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    title = db.query(Title).filter(Title.id == id, Title.is_active == True).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    title.is_active = False

    # Collect listing IDs to cascade down to time slots
    listing_ids = [row.id for row in db.query(Listing.id).filter(Listing.title_id == id).all()]

    # Cascade: deactivate all time slots under those listings (bookings are left untouched)
    if listing_ids:
        db.query(TimeSlot).filter(
            TimeSlot.listing_id.in_(listing_ids),
            TimeSlot.is_active == True,  # noqa: E712
        ).update({"is_active": False}, synchronize_session="fetch")

    # Cascade: deactivate all linked listings
    db.query(Listing).filter(Listing.title_id == id).update({"status": "inactive"})

    db.commit()
    return {
        "id": str(id),
        "is_active": False,
        "message": "Title soft-deleted. All linked listings and time slots deactivated.",
    }


# ---------------------------------------------------------------------------
# Title Images
# ---------------------------------------------------------------------------


@router.post(
    "/{title_id}/images",
    response_model=List[TitleImageSchema],
    status_code=status.HTTP_201_CREATED,
)
def add_images(
    title_id: UUID,
    data: List[TitleImageCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    title = db.query(Title).filter(Title.id == title_id, Title.is_active == True).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    images = []
    for img_data in data:
        image = TitleImage(title_id=title_id, **img_data.model_dump())
        db.add(image)
        images.append(image)

    db.commit()
    for img in images:
        db.refresh(img)
    return images


@router.delete("/{title_id}/images/{img_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_image(
    title_id: UUID,
    img_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    image = (
        db.query(TitleImage)
        .filter(TitleImage.id == img_id, TitleImage.title_id == title_id)
        .first()
    )
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    db.delete(image)
    db.commit()


# ---------------------------------------------------------------------------
# Listings (venue assignments for a title)
# ---------------------------------------------------------------------------


@router.post(
    "/{title_id}/listings",
    response_model=List[ListingSchema],
    status_code=status.HTTP_201_CREATED,
)
def add_listings(
    title_id: UUID,
    data: List[ListingCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    title = db.query(Title).filter(Title.id == title_id, Title.is_active == True).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    # Clean up expired listings first to free up slots
    _expire_stale_listings(db)

    listings = []
    for listing_data in data:
        # Look up venue to auto-populate city
        venue = (
            db.query(Venue)
            .filter(Venue.id == listing_data.venue_id, Venue.is_active == True)
            .first()
        )
        if not venue:
            raise HTTPException(
                status_code=404,
                detail=f"Venue {listing_data.venue_id} not found or inactive",
            )

        # Check for duplicate listing (same title + venue) — only among active listings
        existing = (
            db.query(Listing)
            .filter(
                Listing.title_id == title_id,
                Listing.venue_id == listing_data.venue_id,
                Listing.status == "active",
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Listing already exists for venue '{venue.name}' on this title",
            )

        # Extract time_slots before dumping to model (not a Listing column)
        inline_slots = listing_data.time_slots or []
        listing_dict = listing_data.model_dump(exclude={"time_slots"})

        listing = Listing(
            title_id=title_id,
            city=venue.city,
            created_by=current_user.id,
            **listing_dict,
        )
        db.add(listing)
        db.flush()  # get listing.id for time slots

        # Create inline time slots with overlap checking
        from app.api.v1.admin.time_slots import _check_hall_overlap, _check_not_in_past
        from datetime import time as dt_time

        for ts in inline_slots:
            # Reject past date/time
            start_parsed = dt_time.fromisoformat(ts.start_time)
            _check_not_in_past(ts.slot_date, start_parsed)

            # Validate hall belongs to this venue
            hall = (
                db.query(Hall)
                .filter(
                    Hall.id == ts.hall_id,
                    Hall.venue_id == venue.id,
                    Hall.is_active == True,
                )
                .first()
            )
            if not hall:
                raise HTTPException(
                    status_code=404,
                    detail=f"Hall {ts.hall_id} not found in venue '{venue.name}'",
                )

            # Parse time strings (start already parsed above for past-check)
            start = start_parsed
            end = dt_time.fromisoformat(ts.end_time)

            # Check for overlap in this hall
            _check_hall_overlap(
                db,
                hall_id=ts.hall_id,
                slot_date=ts.slot_date,
                start_time=start,
                end_time=end,
            )

            slot = TimeSlot(
                listing_id=listing.id,
                hall_id=ts.hall_id,
                slot_date=ts.slot_date,
                start_time=start,
                end_time=end,
                capacity=ts.capacity,
                price_override=ts.price_override,
            )
            db.add(slot)

        listings.append(listing)

    db.commit()
    for lst in listings:
        db.refresh(lst)
    return listings


@listing_router.patch("/{id}", response_model=ListingSchema)
def update_listing(
    id: UUID,
    data: ListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    listing = db.query(Listing).filter(Listing.id == id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)

    db.commit()
    db.refresh(listing)
    return listing


@listing_router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_listing(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    listing = db.query(Listing).filter(Listing.id == id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    listing.status = "inactive"
    db.query(TimeSlot).filter(
        TimeSlot.listing_id == id,
        TimeSlot.is_active == True,
    ).update({"is_active": False}, synchronize_session="fetch")
    db.commit()
    return {"id": str(id), "status": "inactive"}


# ---------------------------------------------------------------------------
# Bulk Listing Upload
# ---------------------------------------------------------------------------


@router.post(
    "/{title_id}/bulk-listings",
    response_model=BulkListingResponse,
    status_code=status.HTTP_207_MULTI_STATUS,
)
def bulk_create_listings(
    title_id: UUID,
    data: BulkListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Bulk-create listings (one per venue/cinema) with timeslots in a single request.

    Each entry in `entries` maps to one venue. Within each entry, `slots` defines
    the individual hall+date+time combinations to schedule.

    **Conflict handling (`on_conflict`)**:
    - `"skip"` *(default)*: hall conflicts and duplicate slots are skipped; the rest
      of the request is committed and the response details every skip.
    - `"fail"`: if *any* hall conflict is detected the entire request is rejected
      with HTTP 409 and a full breakdown of all conflicts so the admin can fix the
      modal before resubmitting.
    """
    from datetime import datetime as dt
    from sqlalchemy import or_
    from app.api.v1.admin.time_slots import _check_hall_overlap

    if data.on_conflict not in ("skip", "fail"):
        raise HTTPException(status_code=400, detail="on_conflict must be 'skip' or 'fail'")

    title = db.query(Title).filter(Title.id == title_id, Title.is_active == True).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    _expire_stale_listings(db)

    now = dt.now()
    results = []
    all_conflicts = []   # collected when on_conflict == "fail"

    # ------------------------------------------------------------------
    # First pass: validate everything and build the full result structure.
    # Nothing is written to the DB yet so we can abort cleanly on "fail".
    # ------------------------------------------------------------------
    plan = []  # list of dicts ready to persist

    for entry in data.entries:
        venue = (
            db.query(Venue)
            .filter(Venue.id == entry.venue_id, Venue.is_active == True)
            .first()
        )
        if not venue:
            raise HTTPException(
                status_code=404,
                detail=f"Venue {entry.venue_id} not found or inactive",
            )

        # Check for an already-active listing for this title + venue
        existing_listing = (
            db.query(Listing)
            .filter(
                Listing.title_id == title_id,
                Listing.venue_id == entry.venue_id,
                Listing.status == "active",
            )
            .first()
        )

        listing_result = {
            "venue_id": entry.venue_id,
            "venue_name": venue.name,
            "city": venue.city,
            "listing_status": None,
            "listing_id": None,
            "skip_reason": None,
            "slots": [],
            # internal — not serialised
            "_entry": entry,
            "_venue": venue,
            "_existing_listing": existing_listing,
        }

        slot_plans = []
        for slot_in in entry.slots:
            # Validate hall belongs to this venue
            hall = (
                db.query(Hall)
                .filter(
                    Hall.id == slot_in.hall_id,
                    Hall.venue_id == venue.id,
                    Hall.is_active == True,
                )
                .first()
            )
            if not hall:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Hall {slot_in.hall_id} not found in venue '{venue.name}'"
                    ),
                )

            # Past-time check
            if dt.combine(slot_in.slot_date, slot_in.start_time) < now:
                slot_plans.append({
                    "hall": hall,
                    "slot_in": slot_in,
                    "status": "past",
                    "conflict_detail": "Slot date/time is in the past",
                })
                continue

            # Hall overlap check — query DB
            conflict_slot = (
                db.query(TimeSlot)
                .filter(
                    TimeSlot.hall_id == slot_in.hall_id,
                    TimeSlot.slot_date == slot_in.slot_date,
                    TimeSlot.is_active == True,
                    TimeSlot.start_time < slot_in.end_time,
                    or_(
                        TimeSlot.end_time == None,
                        TimeSlot.end_time > slot_in.start_time,
                    ),
                )
                .first()
            )

            if conflict_slot:
                detail = (
                    f"Hall '{hall.name}' is occupied "
                    f"{conflict_slot.start_time}–{conflict_slot.end_time} "
                    f"on {slot_in.slot_date} (slot {conflict_slot.id})"
                )
                slot_plans.append({
                    "hall": hall,
                    "slot_in": slot_in,
                    "status": "conflict",
                    "conflict_detail": detail,
                })
                all_conflicts.append(detail)
                continue

            # Duplicate check: same listing+date+start already exists
            # (will only matter if existing_listing is reused — handled below)
            slot_plans.append({
                "hall": hall,
                "slot_in": slot_in,
                "status": "ok",
                "conflict_detail": None,
            })

        listing_result["_slot_plans"] = slot_plans
        plan.append(listing_result)

    # ------------------------------------------------------------------
    # Abort early if on_conflict == "fail" and any conflicts found
    # ------------------------------------------------------------------
    if data.on_conflict == "fail" and all_conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": (
                    f"{len(all_conflicts)} hall conflict(s) detected. "
                    "Fix the conflicts and resubmit."
                ),
                "conflicts": all_conflicts,
            },
        )

    # ------------------------------------------------------------------
    # Second pass: persist
    # ------------------------------------------------------------------
    slots_created = 0
    slots_skipped = 0
    conflict_count = 0
    listings_created = 0
    listings_skipped = 0

    for listing_plan in plan:
        entry = listing_plan["_entry"]
        venue = listing_plan["_venue"]
        existing_listing = listing_plan["_existing_listing"]
        slot_plans = listing_plan["_slot_plans"]

        # Decide whether we're creating a new listing or reusing existing
        if existing_listing:
            listing_obj = existing_listing
            listing_plan["listing_status"] = "skipped"
            listing_plan["listing_id"] = existing_listing.id
            listing_plan["skip_reason"] = "Active listing already exists for this venue"
            listings_skipped += 1
        else:
            listing_obj = Listing(
                title_id=title_id,
                venue_id=entry.venue_id,
                city=venue.city,
                price=entry.price,
                currency=entry.currency,
                start_datetime=entry.start_datetime,
                end_datetime=entry.end_datetime,
                total_capacity=entry.total_capacity,
                created_by=current_user.id,
            )
            db.add(listing_obj)
            db.flush()  # get listing_obj.id
            listing_plan["listing_status"] = "created"
            listing_plan["listing_id"] = listing_obj.id
            listings_created += 1

        slot_results = []
        for sp in slot_plans:
            hall = sp["hall"]
            slot_in = sp["slot_in"]

            if sp["status"] != "ok":
                # past / conflict — skip, record
                slot_results.append({
                    "hall_id": slot_in.hall_id,
                    "hall_name": hall.name,
                    "slot_date": slot_in.slot_date,
                    "start_time": slot_in.start_time,
                    "end_time": slot_in.end_time,
                    "status": sp["status"],
                    "slot_id": None,
                    "conflict_detail": sp["conflict_detail"],
                })
                if sp["status"] == "conflict":
                    conflict_count += 1
                slots_skipped += 1
                continue

            # Check for duplicate within an existing listing
            if existing_listing:
                dup = (
                    db.query(TimeSlot)
                    .filter(
                        TimeSlot.listing_id == listing_obj.id,
                        TimeSlot.slot_date == slot_in.slot_date,
                        TimeSlot.start_time == slot_in.start_time,
                        TimeSlot.hall_id == slot_in.hall_id,
                        TimeSlot.is_active == True,
                    )
                    .first()
                )
                if dup:
                    slot_results.append({
                        "hall_id": slot_in.hall_id,
                        "hall_name": hall.name,
                        "slot_date": slot_in.slot_date,
                        "start_time": slot_in.start_time,
                        "end_time": slot_in.end_time,
                        "status": "duplicate",
                        "slot_id": dup.id,
                        "conflict_detail": "Identical slot already exists on this listing",
                    })
                    slots_skipped += 1
                    continue

            new_slot = TimeSlot(
                listing_id=listing_obj.id,
                hall_id=slot_in.hall_id,
                slot_date=slot_in.slot_date,
                start_time=slot_in.start_time,
                end_time=slot_in.end_time,
                capacity=slot_in.capacity,
                price_override=slot_in.price_override,
                slot_type=slot_in.slot_type,
                discount_percent=slot_in.discount_percent,
            )
            db.add(new_slot)
            db.flush()

            slot_results.append({
                "hall_id": slot_in.hall_id,
                "hall_name": hall.name,
                "slot_date": slot_in.slot_date,
                "start_time": slot_in.start_time,
                "end_time": slot_in.end_time,
                "status": "created",
                "slot_id": new_slot.id,
                "conflict_detail": None,
            })
            slots_created += 1

        listing_plan["slots"] = slot_results

    db.commit()

    # Build response
    result_items = []
    for lp in plan:
        from app.schemas.time_slot import ListingBulkResult, SlotBulkResult
        result_items.append(
            ListingBulkResult(
                venue_id=lp["venue_id"],
                venue_name=lp["venue_name"],
                city=lp["city"],
                listing_status=lp["listing_status"],
                listing_id=lp["listing_id"],
                skip_reason=lp["skip_reason"],
                slots=[SlotBulkResult(**s) for s in lp["slots"]],
            )
        )

    from app.schemas.time_slot import BulkListingSummary
    return BulkListingResponse(
        summary=BulkListingSummary(
            total_entries=len(plan),
            listings_created=listings_created,
            listings_skipped=listings_skipped,
            slots_created=slots_created,
            slots_skipped=slots_skipped,
            conflict_count=conflict_count,
        ),
        results=result_items,
    )
