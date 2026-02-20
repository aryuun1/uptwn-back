from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.title import Title
from app.models.listing import Listing
from app.models.booking import Booking
from app.models.review_notification import Review
from app.schemas.review_notification import ReviewCreate, Review as ReviewSchema
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/titles", tags=["Reviews"])


@router.post("/{slug}/reviews", response_model=ReviewSchema, status_code=201)
def submit_review(
    slug: str,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a star rating + optional comment for a title.

    Rules:
    - Rating must be 1–5.
    - User must have at least one confirmed or completed booking for this title.
    - One review per user per title (returns 409 if already reviewed).
    - Updates the title's aggregate `rating` and `rating_count` atomically.
    """
    if not (1 <= data.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    title = db.query(Title).filter(Title.slug == slug, Title.is_active == True).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    # Require the user to have booked this title
    has_booking = (
        db.query(Booking)
        .join(Listing, Listing.id == Booking.listing_id)
        .filter(
            Booking.user_id == current_user.id,
            Listing.title_id == title.id,
            Booking.status.in_(["confirmed", "completed"]),
        )
        .first()
    )
    if not has_booking:
        raise HTTPException(
            status_code=403,
            detail="You must have a booking for this title to leave a review",
        )

    # One review per user per title
    if db.query(Review).filter(
        Review.user_id == current_user.id, Review.title_id == title.id
    ).first():
        raise HTTPException(status_code=409, detail="You have already reviewed this title")

    review = Review(
        user_id=current_user.id,
        title_id=title.id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    db.flush()

    # Update aggregate rating on the title
    new_count = title.rating_count + 1
    new_rating = ((float(title.rating) * title.rating_count) + data.rating) / new_count
    title.rating_count = new_count
    title.rating = round(new_rating, 1)

    db.commit()
    db.refresh(review)
    return review


@router.get("/{slug}/reviews", response_model=PaginatedResponse[ReviewSchema])
def list_reviews(
    slug: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Return paginated reviews for a title. No authentication required."""
    title = db.query(Title).filter(Title.slug == slug, Title.is_active == True).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    query = db.query(Review).filter(Review.title_id == title.id)
    total = query.count()
    reviews = (
        query.order_by(Review.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        data=reviews,
        total=total,
        page=page,
        limit=limit,
        total_pages=-(-total // limit) if total else 0,
    )
