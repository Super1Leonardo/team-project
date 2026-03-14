from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.channels import TARGET_CHANNELS
from backend.config import get_settings
from backend.models import (
    AppConfigResponse,
    AuthMethodsResponse,
    AuthSendCodeRequest,
    AuthVerifyCodeRequest,
    PasswordRequest,
)
from backend.telegram_service import (
    TelegramCodeNotRequestedError,
    TelegramConfigurationError,
    TelegramPasswordRequiredError,
    TelegramService,
    TelegramServiceError,
    TelegramUnauthorizedError,
)
from backend.ui import render_app_html

settings = get_settings()
telegram_service = TelegramService(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.telegram_session_path.parent.mkdir(parents=True, exist_ok=True)
    yield


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


def _handle_telegram_error(exc: Exception) -> HTTPException:
    if isinstance(exc, TelegramConfigurationError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, TelegramUnauthorizedError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, TelegramPasswordRequiredError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, TelegramCodeNotRequestedError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, TelegramServiceError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected server error.")


@app.get("/", response_class=HTMLResponse)
async def app_ui():
    return HTMLResponse(render_app_html())


@app.get("/api/health")
async def healthcheck():
    return {"status": "ok"}


@app.get("/api/app-config", response_model=AppConfigResponse)
async def app_config():
    return AppConfigResponse(
        api_title=settings.api_title,
        api_version=settings.api_version,
        public_api_url=settings.public_backend_api_url,
        selected_channels=TARGET_CHANNELS,
        auth_methods=AuthMethodsResponse(code=True, qr=True),
        docs_url="/docs",
        health_url="/api/health",
    )


@app.get("/api/channels")
async def list_channels():
    return {"channels": TARGET_CHANNELS}


@app.get("/api/telegram/auth/status")
async def telegram_auth_status():
    try:
        return await telegram_service.get_auth_status()
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc


@app.post("/api/telegram/auth/qr/start")
async def start_qr_login(recreate: bool = False):
    try:
        return await telegram_service.start_qr_login(recreate=recreate)
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc


@app.get("/api/telegram/auth/qr/status")
async def qr_login_status():
    try:
        return await telegram_service.get_qr_login_status()
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc


@app.post("/api/telegram/auth/qr/password")
async def qr_login_password(payload: PasswordRequest):
    try:
        return await telegram_service.verify_qr_password(password=payload.password)
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc


@app.post("/api/telegram/auth/qr/cancel")
async def cancel_qr_login():
    try:
        return await telegram_service.cancel_qr_login()
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc


@app.post("/api/telegram/auth/send-code")
async def send_auth_code(payload: AuthSendCodeRequest):
    try:
        return await telegram_service.send_code(phone=payload.phone)
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc


@app.post("/api/telegram/auth/verify-code")
async def verify_auth_code(payload: AuthVerifyCodeRequest):
    try:
        return await telegram_service.verify_code(
            code=payload.code,
            phone=payload.phone,
            password=payload.password,
        )
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc


@app.post("/api/telegram/auth/logout")
async def logout():
    try:
        return await telegram_service.logout()
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc


@app.get("/api/messages")
async def parse_messages(
    limit_per_channel: int = Query(default=20, ge=1, le=100),
    channel: list[str] | None = Query(default=None),
):
    try:
        return await telegram_service.parse_configured_channels(
            limit_per_channel=limit_per_channel,
            channels=channel,
        )
    except Exception as exc:
        raise _handle_telegram_error(exc) from exc
