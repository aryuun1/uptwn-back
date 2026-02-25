from uuid import UUID
from typing import Optional
from datetime import date
from decimal import Decimal
from calendar import monthrange

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date as SQLDate

from app.db.session import get_db
from app.api.deps import get_current_admin_user
from app.models.user import User
from app.models.booking import Booking
from app.models.listing import Listing
from app.models.title import Title, CategoryType
from app.models.venue import Venue
from app.schemas.revenue import (
    RevenueResponse,
    RevenueSummary,
    TimeSeriesPoint,
    CategoryBreakdown,
    CityBreakdown,
    TitleBreakdown,
    VenueBreakdown,
)

router = APIRouter(prefix="/admin/revenue", tags=["Admin - Revenue"])

# Statuses that represent real collected money
PAID_STATUSES = ("confirmed", "completed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dimension_filters(
    date_from, date_to, category, title_slug, venue_id, city
):
    """Filters shared by every sub-query (no status filter here)."""
    filters = []
    if date_from:
        filters.append(cast(Booking.booking_date, SQLDate) >= date_from)
    if date_to:
        filters.append(cast(Booking.booking_date, SQLDate) <= date_to)
    if category:
        filters.append(Title.category == category)
    if title_slug:
        filters.append(Title.slug == title_slug)
    if venue_id:
        filters.append(Listing.venue_id == venue_id)
    if city:
        filters.append(Listing.city.ilike(f"%{city}%"))
    return filters


def _base(db: Session):
    """Base query with all required joins."""
    return (
        db.query(Booking)
        .join(Listing, Listing.id == Booking.listing_id)
        .join(Title, Title.id == Listing.title_id)
        .outerjoin(Venue, Venue.id == Listing.venue_id)
    )


# ---------------------------------------------------------------------------
# Revenue endpoint
# ---------------------------------------------------------------------------


@router.get("/", response_model=RevenueResponse)
def get_revenue(
    # --- Date range (applied to booking_date — when money was collected) ---
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    year: Optional[int] = Query(None, ge=2020, le=2100, description="Filter entire year"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter a specific month (requires year)"),

    # --- Dimension filters ---
    category: Optional[CategoryType] = Query(None, description="movies | events | restaurants"),
    title_slug: Optional[str] = Query(None, description="Filter by a specific title"),
    venue_id: Optional[UUID] = Query(None, description="Filter by a specific venue"),
    city: Optional[str] = Query(None, description="Filter by city (case-insensitive)"),

    # --- Time series grouping ---
    group_by: str = Query("month", pattern="^(day|month|year)$", description="Time-series granularity"),

    # --- Cancelled handling ---
    include_cancelled: bool = Query(
        False,
        description=(
            "Include cancelled bookings in main revenue totals. "
            "Cancelled stats are always shown separately regardless."
        ),
    ),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Revenue analytics dashboard for financial reporting.

    **Date filtering** (all applied on `booking_date` — when the payment was made):
    - Use `date_from` / `date_to` for a custom range.
    - Use `year` alone for a full calendar year.
    - Use `year` + `month` for a specific month.

    **Dimension filters** can be combined freely:
    `category`, `title_slug`, `venue_id`, `city`.

    **Response includes:**
    - `summary` — totals + cancelled stats
    - `time_series` — revenue over time (granularity set by `group_by`)
    - `by_category` — breakdown per event type
    - `by_city` — breakdown per city
    - `by_title` — top 20 titles by revenue
    - `by_venue` — top 20 venues by revenue
    """
    # Resolve year/month convenience params into date_from / date_to
    if year and not date_from and not date_to:
        if month:
            last_day = monthrange(year, month)[1]
            date_from = date(year, month, 1)
            date_to = date(year, month, last_day)
        else:
            date_from = date(year, 1, 1)
            date_to = date(year, 12, 31)

    if month and not year:
        raise HTTPException(
            status_code=400, detail="Provide `year` alongside `month`."
        )

    dim = _dimension_filters(date_from, date_to, category, title_slug, venue_id, city)

    paid_statuses = list(PAID_STATUSES) + (["cancelled"] if include_cancelled else [])
    revenue_filters = [Booking.status.in_(paid_statuses)] + dim
    cancelled_filters = [Booking.status == "cancelled"] + dim

    def format_period(dt) -> str:
        if group_by == "day":
            return dt.strftime("%Y-%m-%d")
        elif group_by == "month":
            return dt.strftime("%Y-%m")
        return dt.strftime("%Y")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    s = (
        _base(db)
        .with_entities(
            func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"),
            func.count(Booking.id).label("bookings"),
            func.coalesce(func.sum(Booking.quantity), 0).label("tickets"),
        )
        .filter(*revenue_filters)
        .one()
    )

    avg = (
        Decimal(str(s.revenue)) / s.bookings
        if s.bookings > 0
        else Decimal("0.00")
    )

    c = (
        _base(db)
        .with_entities(
            func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"),
            func.count(Booking.id).label("bookings"),
        )
        .filter(*cancelled_filters)
        .one()
    )

    summary = RevenueSummary(
        total_revenue=s.revenue,
        total_bookings=s.bookings,
        total_tickets=s.tickets,
        avg_per_booking=avg,
        cancelled_revenue=c.revenue,
        cancelled_bookings=c.bookings,
    )

    # ------------------------------------------------------------------
    # Time series
    # ------------------------------------------------------------------
    trunc = func.date_trunc(group_by, Booking.booking_date).label("period")

    ts_rows = (
        _base(db)
        .with_entities(
            trunc,
            func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"),
            func.count(Booking.id).label("bookings"),
            func.coalesce(func.sum(Booking.quantity), 0).label("tickets"),
        )
        .filter(*revenue_filters)
        .group_by(trunc)
        .order_by(trunc)
        .all()
    )

    time_series = [
        TimeSeriesPoint(
            period=format_period(r.period),
            revenue=r.revenue,
            bookings=r.bookings,
            tickets=r.tickets,
        )
        for r in ts_rows
    ]

    # ------------------------------------------------------------------
    # By category
    # ------------------------------------------------------------------
    cat_rows = (
        _base(db)
        .with_entities(
            Title.category.label("category"),
            func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"),
            func.count(Booking.id).label("bookings"),
            func.coalesce(func.sum(Booking.quantity), 0).label("tickets"),
        )
        .filter(*revenue_filters)
        .group_by(Title.category)
        .order_by(func.sum(Booking.total_amount).desc())
        .all()
    )

    by_category = [
        CategoryBreakdown(
            category=r.category,
            revenue=r.revenue,
            bookings=r.bookings,
            tickets=r.tickets,
        )
        for r in cat_rows
    ]

    # ------------------------------------------------------------------
    # By city
    # ------------------------------------------------------------------
    city_rows = (
        _base(db)
        .with_entities(
            Listing.city.label("city"),
            func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"),
            func.count(Booking.id).label("bookings"),
            func.coalesce(func.sum(Booking.quantity), 0).label("tickets"),
        )
        .filter(*revenue_filters, Listing.city != None)  # noqa: E711
        .group_by(Listing.city)
        .order_by(func.sum(Booking.total_amount).desc())
        .all()
    )

    by_city = [
        CityBreakdown(
            city=r.city,
            revenue=r.revenue,
            bookings=r.bookings,
            tickets=r.tickets,
        )
        for r in city_rows
    ]

    # ------------------------------------------------------------------
    # By title (top 20)
    # ------------------------------------------------------------------
    title_rows = (
        _base(db)
        .with_entities(
            Title.title.label("title"),
            Title.slug.label("slug"),
            Title.category.label("category"),
            func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"),
            func.count(Booking.id).label("bookings"),
            func.coalesce(func.sum(Booking.quantity), 0).label("tickets"),
        )
        .filter(*revenue_filters)
        .group_by(Title.title, Title.slug, Title.category)
        .order_by(func.sum(Booking.total_amount).desc())
        .limit(20)
        .all()
    )

    by_title = [
        TitleBreakdown(
            title=r.title,
            slug=r.slug,
            category=r.category,
            revenue=r.revenue,
            bookings=r.bookings,
            tickets=r.tickets,
        )
        for r in title_rows
    ]

    # ------------------------------------------------------------------
    # By venue (top 20) — inner join so only listings with a venue appear
    # ------------------------------------------------------------------
    venue_rows = (
        db.query(Booking)
        .join(Listing, Listing.id == Booking.listing_id)
        .join(Title, Title.id == Listing.title_id)
        .join(Venue, Venue.id == Listing.venue_id)
        .with_entities(
            Venue.id.label("venue_id"),
            Venue.name.label("venue_name"),
            Venue.city.label("city"),
            func.coalesce(func.sum(Booking.total_amount), 0).label("revenue"),
            func.count(Booking.id).label("bookings"),
            func.coalesce(func.sum(Booking.quantity), 0).label("tickets"),
        )
        .filter(*revenue_filters)
        .group_by(Venue.id, Venue.name, Venue.city)
        .order_by(func.sum(Booking.total_amount).desc())
        .limit(20)
        .all()
    )

    by_venue = [
        VenueBreakdown(
            venue_id=r.venue_id,
            venue_name=r.venue_name,
            city=r.city,
            revenue=r.revenue,
            bookings=r.bookings,
            tickets=r.tickets,
        )
        for r in venue_rows
    ]

    return RevenueResponse(
        summary=summary,
        time_series=time_series,
        by_category=by_category,
        by_city=by_city,
        by_title=by_title,
        by_venue=by_venue,
    )
