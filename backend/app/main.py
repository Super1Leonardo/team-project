import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.dependencies import get_app_settings, get_brandradar_runtime
from backend.app.api.router import api_router
from backend.app.core.exception_handlers import register_exception_handlers
from backend.app.infra.db.clickhouse import ClickHouseMentionEventsStore
from backend.app.infra.db.postgres import BrandRadarPostgresStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_app_settings()
    settings.telegram_session_path.parent.mkdir(parents=True, exist_ok=True)
    BrandRadarPostgresStore(settings).init_db()
    ClickHouseMentionEventsStore(settings).init_db()
    runtime = get_brandradar_runtime()
    stop_event = asyncio.Event()
    worker_tasks = [
        asyncio.create_task(
            runtime.collector_worker.run_forever(stop_event),
            name="brandradar-collector-worker",
        ),
        asyncio.create_task(
            runtime.ml_worker.run_forever(stop_event),
            name="brandradar-ml-worker",
        ),
    ]
    app.state.brandradar_runtime = runtime
    app.state.brandradar_worker_stop_event = stop_event
    app.state.brandradar_worker_tasks = worker_tasks

    try:
        yield
    finally:
        stop_event.set()
        await asyncio.gather(*worker_tasks, return_exceptions=True)


def create_app() -> FastAPI:
    settings = get_app_settings()
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
