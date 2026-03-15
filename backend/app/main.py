from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.core.config import APP_NAME
from app.db.database import create_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
app.include_router(health_router)
app.include_router(documents_router)
