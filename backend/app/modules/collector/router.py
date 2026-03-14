from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import get_collector_service
from backend.app.modules.collector.schemas import (
    AuthSendCodeRequest,
    AuthStatusResponse,
    AuthVerifyCodeRequest,
    ParseResponse,
    PasswordRequest,
    QrLoginResponse,
)
from backend.app.modules.collector.service import CollectorService

router = APIRouter(tags=["collector"])


@router.get("/telegram/auth/status", response_model=AuthStatusResponse)
async def telegram_auth_status(
    service: CollectorService = Depends(get_collector_service),
):
    return await service.get_auth_status()


@router.post("/telegram/auth/qr/start", response_model=QrLoginResponse)
async def start_qr_login(
    recreate: bool = False,
    service: CollectorService = Depends(get_collector_service),
):
    return await service.start_qr_login(recreate=recreate)


@router.get("/telegram/auth/qr/status", response_model=QrLoginResponse)
async def qr_login_status(service: CollectorService = Depends(get_collector_service)):
    return await service.get_qr_login_status()


@router.post("/telegram/auth/qr/password", response_model=QrLoginResponse)
async def qr_login_password(
    payload: PasswordRequest,
    service: CollectorService = Depends(get_collector_service),
):
    return await service.verify_qr_password(payload)


@router.post("/telegram/auth/qr/cancel", response_model=QrLoginResponse)
async def cancel_qr_login(service: CollectorService = Depends(get_collector_service)):
    return await service.cancel_qr_login()


@router.post("/telegram/auth/send-code")
async def send_auth_code(
    payload: AuthSendCodeRequest,
    service: CollectorService = Depends(get_collector_service),
):
    return await service.send_auth_code(payload)


@router.post("/telegram/auth/verify-code")
async def verify_auth_code(
    payload: AuthVerifyCodeRequest,
    service: CollectorService = Depends(get_collector_service),
):
    return await service.verify_auth_code(payload)


@router.post("/telegram/auth/logout")
async def logout(service: CollectorService = Depends(get_collector_service)):
    return await service.logout()


@router.get("/messages", response_model=ParseResponse)
async def parse_messages(
    limit_per_channel: int = Query(default=20, ge=1, le=100),
    channel: list[str] | None = Query(default=None),
    store: bool = Query(default=True),
    service: CollectorService = Depends(get_collector_service),
):
    return await service.collect_messages(
        limit_per_channel=limit_per_channel,
        channel=channel,
        store=store,
    )
