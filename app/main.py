from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.init_db import create_database
from app.db.base import Base
from app.db.session import engine
from app.core.config import settings
from app.api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB exists and create tables
    create_database()
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: Clean up if needed


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