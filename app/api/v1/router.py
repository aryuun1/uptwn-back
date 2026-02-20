
from fastapi import APIRouter

# Auth
from app.api.v1.public.auth import router as auth_router

# Public — discovery
from app.api.v1.public.titles import router as public_titles_router
from app.api.v1.public.listings import router as public_listings_router

# Public — time slots, seat map, locks, holds
from app.api.v1.public.time_slots import (
    listing_slots_router,
    slot_public_router,
)

# Public — bookings
from app.api.v1.public.bookings import router as bookings_router

# Public — user profile & notifications
from app.api.v1.public.me import router as me_router

# Public — reviews
from app.api.v1.public.reviews import router as reviews_router

# Admin
from app.api.v1.admin.venues import router as venues_router, hall_router
from app.api.v1.admin.seats import seats_router, seat_router
from app.api.v1.admin.titles import router as titles_router, listing_router
from app.api.v1.admin.time_slots import (
    router as time_slot_router,
    slot_router,
    hall_schedule_router,
    venue_schedule_router,
)

api_router = APIRouter()

# --- Auth ---
api_router.include_router(auth_router)

# --- Public: discovery ---
api_router.include_router(public_titles_router)
api_router.include_router(public_listings_router)

# --- Public: time slots (adds /{listing_id}/time-slots to /listings prefix) ---
api_router.include_router(listing_slots_router)
api_router.include_router(slot_public_router)

# --- Public: bookings ---
api_router.include_router(bookings_router)

# --- Public: profile & notifications ---
api_router.include_router(me_router)

# --- Public: reviews ---
api_router.include_router(reviews_router)

# --- Admin ---
api_router.include_router(venues_router)
api_router.include_router(hall_router)
api_router.include_router(seats_router)
api_router.include_router(seat_router)
api_router.include_router(titles_router)
api_router.include_router(listing_router)
api_router.include_router(time_slot_router)
api_router.include_router(slot_router)
api_router.include_router(hall_schedule_router)
api_router.include_router(venue_schedule_router)
