from typing import Optional, List
from pydantic import BaseModel, UUID4
from decimal import Decimal
from datetime import date


class RevenueSummary(BaseModel):
    total_revenue: Decimal
    total_bookings: int
    total_tickets: int
    avg_per_booking: Decimal
    # Always computed separately — not affected by include_cancelled flag
    cancelled_revenue: Decimal
    cancelled_bookings: int


class TimeSeriesPoint(BaseModel):
    period: str          # "2026-02-25" | "2026-02" | "2026"
    revenue: Decimal
    bookings: int
    tickets: int


class CategoryBreakdown(BaseModel):
    category: str
    revenue: Decimal
    bookings: int
    tickets: int


class CityBreakdown(BaseModel):
    city: str
    revenue: Decimal
    bookings: int
    tickets: int


class TitleBreakdown(BaseModel):
    title: str
    slug: str
    category: str
    revenue: Decimal
    bookings: int
    tickets: int


class VenueBreakdown(BaseModel):
    venue_id: UUID4
    venue_name: str
    city: str
    revenue: Decimal
    bookings: int
    tickets: int


class RevenueResponse(BaseModel):
    summary: RevenueSummary
    time_series: List[TimeSeriesPoint]
    by_category: List[CategoryBreakdown]
    by_city: List[CityBreakdown]
    by_title: List[TitleBreakdown]
    by_venue: List[VenueBreakdown]
