from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: Literal["ok"] = "ok"
    app_name: str
    environment: str
