import asyncio

from fastapi import APIRouter, Response

from app import cache, db
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(response: Response) -> HealthResponse:
    db_ok, redis_ok = await asyncio.gather(db.check_db(), cache.check_redis())
    if not (db_ok and redis_ok):
        response.status_code = 503
    return HealthResponse(
        status="ok" if db_ok and redis_ok else "degraded",
        db="ok" if db_ok else "error",
        redis="ok" if redis_ok else "error",
    )
