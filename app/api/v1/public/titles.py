from uuid import UUID
from typing import List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.title import Title, CategoryType
from app.models.listing import Listing
from app.schemas.title import TitleBrowseCard, TitleDetail, TitleSearchResult
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/titles", tags=["Titles"])


@router.get("/", response_model=PaginatedResponse[TitleBrowseCard])
def list_titles(
    category: Optional[CategoryType] = None,
    city: Optional[str] = None,
    featured: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Title).filter(Title.is_active == True)

    if category:
        query = query.filter(Title.category == category)
    if featured is not None:
        query = query.filter(Title.is_featured == featured)
        # Without city context, local featured events have no meaningful scope —
        # only national ones should surface globally
        if featured and not city:
            query = query.filter(Title.scope == "national")
    if search:
        query = query.filter(Title.title.ilike(f"%{search}%"))

    # Local titles: only show if they have an active listing in the user's city
    # National titles: always show regardless of city context
    if city:
        query = query.filter(
            or_(
                Title.scope == "national",
                Title.id.in_(
                    db.query(Listing.title_id)
                    .filter(Listing.city.ilike(city), Listing.status == "active")
                ),
            )
        )

    total = query.count()
    titles = query.order_by(Title.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    # Build browse cards with aggregated listing info
    results = []
    for t in titles:
        active_listings = [l for l in t.listings if l.status == "active"]
        prices = [l.price for l in active_listings if l.price is not None]
        cities = list({l.city for l in active_listings if l.city})

        card = TitleBrowseCard(
            id=t.id,
            category=t.category,
            title=t.title,
            slug=t.slug,
            short_description=t.short_description,
            image_url=t.image_url,
            duration_minutes=t.duration_minutes,
            rating=t.rating,
            rating_count=t.rating_count,
            is_featured=t.is_featured,
            tags=t.tags,
            meta=t.meta,
            scope=t.scope,
            min_price=min(prices) if prices else None,
            venue_count=len(active_listings),
            cities=sorted(cities),
        )
        results.append(card)

    return PaginatedResponse(
        data=results,
        total=total,
        page=page,
        limit=limit,
        total_pages=-(-total // limit) if total else 0,
    )


@router.get("/search", response_model=List[TitleSearchResult])
def search_titles(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Global title search for the home page search bar.
    Returns lightweight results regardless of city — any title
    with at least one active listing is eligible.
    Frontend uses slug to navigate straight to the title page.
    """
    titles = (
        db.query(Title)
        .filter(
            Title.is_active == True,
            Title.title.ilike(f"%{q}%"),
            Title.id.in_(
                db.query(Listing.title_id).filter(Listing.status == "active")
            ),
        )
        .order_by(Title.is_featured.desc(), Title.rating.desc())
        .limit(limit)
        .all()
    )

    results = []
    for t in titles:
        active_listings = [l for l in t.listings if l.status == "active"]
        prices = [l.price for l in active_listings if l.price is not None]
        cities = sorted({l.city for l in active_listings if l.city})

        results.append(
            TitleSearchResult(
                slug=t.slug,
                title=t.title,
                category=t.category,
                image_url=t.image_url,
                cities=cities,
                min_price=min(prices) if prices else None,
            )
        )

    return results


@router.get("/{slug}", response_model=TitleDetail)
def get_title(slug: str, db: Session = Depends(get_db)):
    title = (
        db.query(Title)
        .options(joinedload(Title.images), joinedload(Title.listings).joinedload(Listing.venue))
        .filter(Title.slug == slug, Title.is_active == True)
        .first()
    )
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    # Filter to only active listings, most recent first
    title.listings = sorted(
        [l for l in title.listings if l.status == "active"],
        key=lambda l: l.created_at,
        reverse=True,
    )

    return title
