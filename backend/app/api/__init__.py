from fastapi import APIRouter

from app.api import domains, health, scan

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(scan.router)
api_router.include_router(domains.router)
