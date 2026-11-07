from typing import Literal

from pydantic import BaseModel

ComponentStatus = Literal["ok", "error"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: ComponentStatus
    redis: ComponentStatus
