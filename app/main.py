import asyncio
import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.init_db import create_database
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.core.config import settings
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


async def _slot_cleanup_loop() -> None:
    """Background task: deactivate past time slots every 60 seconds."""
    from app.utils.timeslots import deactivate_past_slots

    while True:
        try:
            db = SessionLocal()
            try:
                count = deactivate_past_slots(db)
                if count:
                    logger.info("Deactivated %d past time slot(s).", count)
            finally:
                db.close()
        except Exception:
            logger.exception("Error during past-slot cleanup.")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB exists and create tables
    create_database()
    Base.metadata.create_all(bind=engine)

    # Run an immediate cleanup, then keep running in the background
    cleanup_task = asyncio.create_task(_slot_cleanup_loop())
    yield

    # Shutdown: cancel background task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Uptwn API", lifespan=lifespan)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"Hello": "Uptwn"}