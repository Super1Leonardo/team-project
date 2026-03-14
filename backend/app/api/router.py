from __future__ import annotations

from fastapi import APIRouter

from app.modules.alerts.router import router as alerts_router
from app.modules.analytics.router import router as analytics_router
from app.modules.brands.router import router as brands_router
from app.modules.collector.router import router as collector_router
from app.modules.events.router import router as events_router
from app.modules.health.router import router as health_router
from app.modules.mentions.router import router as mentions_router
from app.modules.projects.router import router as projects_router
from app.modules.sources.router import router as sources_router
from app.modules.statuses.router import router as statuses_router

router = APIRouter()
router.include_router(projects_router)
router.include_router(brands_router)
router.include_router(sources_router)
router.include_router(collector_router)
router.include_router(mentions_router)
router.include_router(analytics_router)
router.include_router(alerts_router)
router.include_router(events_router)
router.include_router(statuses_router)
router.include_router(health_router)
