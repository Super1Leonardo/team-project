from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.dependencies import build_container
from app.api.router import router as api_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging()

    container = build_container(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container
        yield
        await container.shutdown()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    app.state.container = container
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()
