from fastapi import APIRouter

from backend.app.modules.brandradar.router import router as brandradar_router
from backend.app.modules.collector.router import router as collector_router
from backend.app.modules.health.router import router as parser_health_router
from backend.app.modules.messages.router import router as messages_router
from backend.app.modules.ml.router import router as parser_ml_router
from backend.app.modules.sources.router import router as sources_router

api_router = APIRouter(prefix="/api")
api_router.include_router(brandradar_router)
api_router.include_router(sources_router)
api_router.include_router(collector_router)
api_router.include_router(messages_router)
api_router.include_router(parser_ml_router, prefix="/parser")
api_router.include_router(parser_health_router, prefix="/parser")
