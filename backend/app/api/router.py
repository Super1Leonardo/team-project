from fastapi import APIRouter

from backend.app.modules.brandradar.router import router as brandradar_router

api_router = APIRouter(prefix="/api")
api_router.include_router(brandradar_router)
