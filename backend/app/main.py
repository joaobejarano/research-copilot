from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import APP_NAME

app = FastAPI(title=APP_NAME)
app.include_router(health_router)
