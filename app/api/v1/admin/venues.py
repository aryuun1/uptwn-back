
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.venue import Venue
from app.models.hall import Hall
from app.schemas.venue import (
    VenueCreate,
    VenueUpdate,
    Venue as VenueSchema,
    VenueListItem,
    HallCreate,
    HallUpdate,
    Hall as HallSchema,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/admin/venues", tags=["Admin - Venues"])
hall_router = APIRouter(prefix="/admin/halls", tags=["Admin - Halls"])


# ---------------------------------------------------------------------------
# Venue CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=VenueSchema, status_code=status.HTTP_201_CREATED)
def create_venue(
    data: VenueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    venue = Venue(**data.model_dump())
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


@router.get("/", response_model=PaginatedResponse[VenueListItem])
def list_venues(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    base_query = (
        db.query(Venue, func.count(Hall.id).label("halls_count"))
        .outerjoin(Hall, (Hall.venue_id == Venue.id) & (Hall.is_active == True))
        .filter(Venue.is_active == True)
        .group_by(Venue.id)
    )

    total = db.query(func.count(Venue.id)).filter(Venue.is_active == True).scalar()

    rows = base_query.order_by(Venue.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for venue, halls_count in rows:
        item = VenueListItem.model_validate(venue)
        item.halls_count = halls_count
        items.append(item)

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=-(-total // limit) if total else 0,
    )


@router.patch("/{id}", response_model=VenueSchema)
def update_venue(
    id: UUID,
    data: VenueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    venue = db.query(Venue).filter(Venue.id == id, Venue.is_active == True).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(venue, field, value)

    db.commit()
    db.refresh(venue)
    return venue


@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_venue(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    venue = db.query(Venue).filter(Venue.id == id, Venue.is_active == True).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    venue.is_active = False
    # Cascade: soft-delete all halls in this venue
    db.query(Hall).filter(Hall.venue_id == id, Hall.is_active == True).update(
        {"is_active": False}
    )
    db.commit()
    return {"id": str(id), "is_active": False}


# ---------------------------------------------------------------------------
# Hall CRUD (nested under venues for create/list, flat for update/delete)
# ---------------------------------------------------------------------------


@router.post(
    "/{venue_id}/halls", response_model=HallSchema, status_code=status.HTTP_201_CREATED
)
def create_hall(
    venue_id: UUID,
    data: HallCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    venue = db.query(Venue).filter(Venue.id == venue_id, Venue.is_active == True).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    hall = Hall(venue_id=venue_id, **data.model_dump())
    db.add(hall)
    db.commit()
    db.refresh(hall)
    return hall


@router.get("/{venue_id}/halls", response_model=list[HallSchema])
def list_halls(
    venue_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    halls = (
        db.query(Hall)
        .filter(Hall.venue_id == venue_id, Hall.is_active == True)
        .order_by(Hall.name)
        .all()
    )
    return halls


@hall_router.patch("/{id}", response_model=HallSchema)
def update_hall(
    id: UUID,
    data: HallUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    hall = db.query(Hall).filter(Hall.id == id, Hall.is_active == True).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Hall not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(hall, field, value)

    db.commit()
    db.refresh(hall)
    return hall


@hall_router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_hall(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    hall = db.query(Hall).filter(Hall.id == id, Hall.is_active == True).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Hall not found")

    hall.is_active = False
    db.commit()
    return {"id": str(id), "is_active": False}
