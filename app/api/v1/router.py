
from fastapi import APIRouter

from app.api.v1.public.auth import router as auth_router
from app.api.v1.public.titles import router as public_titles_router
from app.api.v1.public.listings import router as public_listings_router
from app.api.v1.admin.venues import router as venues_router, hall_router
from app.api.v1.admin.titles import router as titles_router, listing_router
from app.api.v1.admin.time_slots import router as time_slot_router, slot_router, hall_schedule_router, venue_schedule_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(public_titles_router)
api_router.include_router(public_listings_router)
api_router.include_router(venues_router)
api_router.include_router(hall_router)
api_router.include_router(titles_router)
api_router.include_router(listing_router)
api_router.include_router(time_slot_router)
api_router.include_router(slot_router)
api_router.include_router(hall_schedule_router)
api_router.include_router(venue_schedule_router)
