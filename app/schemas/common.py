
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


# Paginated response wrapper — used by all list endpoints
class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    page: int
    limit: int
    total_pages: int


# Error responses
class ErrorResponse(BaseModel):
    error: str
    message: str


class SeatsUnavailableError(ErrorResponse):
    unavailable_seat_ids: List[str]


class InsufficientCapacityError(ErrorResponse):
    available: int
    requested: int


# Admin dashboard
class CategoryStats(BaseModel):
    count: int


class DashboardStats(BaseModel):
    total_titles: int
    total_bookings: int
    total_revenue: float
    total_users: int
    categories: dict[str, CategoryStats]
