from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.listing import Listing
from app.models.title import Title, CategoryType
from app.schemas.title import ListingWithVenue

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("/", response_model=List[ListingWithVenue])
def list_listings(
    category: Optional[CategoryType] = None,
    city: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Listing)
        .join(Title, Title.id == Listing.title_id)
        .options(joinedload(Listing.venue))
        .filter(Listing.status == "active", Title.is_active == True)
    )

    if category:
        query = query.filter(Title.category == category)
    if city:
        query = query.filter(Listing.city.ilike(city))

    return query.order_by(Listing.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{id}", response_model=ListingWithVenue)
def get_listing(id: UUID, db: Session = Depends(get_db)):
    listing = (
        db.query(Listing)
        .options(joinedload(Listing.venue))
        .filter(Listing.id == id, Listing.status == "active")
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
