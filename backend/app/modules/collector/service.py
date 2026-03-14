from backend.app.core.exceptions import FeatureNotImplementedError
from backend.app.infra.gateways.telegram_gateway import TelegramGateway
from backend.app.modules.collector.schemas import (
    AuthSendCodeRequest,
    AuthStatusResponse,
    AuthVerifyCodeRequest,
    ParseResponse,
    PasswordRequest,
    QrLoginResponse,
)
from backend.app.modules.messages.repository import MessagesRepository
from backend.app.modules.sources.repository import ParserSettingsRepository


class CollectorService:
    def __init__(
        self,
        telegram_gateway: TelegramGateway,
        sources_repository: ParserSettingsRepository,
        messages_repository: MessagesRepository,
    ):
        self.telegram_gateway = telegram_gateway
        self.sources_repository = sources_repository
        self.messages_repository = messages_repository

    async def get_auth_status(self) -> AuthStatusResponse:
        return await self.telegram_gateway.get_auth_status(
            selected_channels=self.sources_repository.selected_telegram_channels
        )

    async def start_qr_login(self, recreate: bool) -> QrLoginResponse:
        return QrLoginResponse.model_validate(
            await self.telegram_gateway.start_qr_login(recreate=recreate)
        )

    async def get_qr_login_status(self) -> QrLoginResponse:
        return QrLoginResponse.model_validate(
            await self.telegram_gateway.get_qr_login_status()
        )

    async def verify_qr_password(self, payload: PasswordRequest) -> QrLoginResponse:
        return QrLoginResponse.model_validate(
            await self.telegram_gateway.verify_qr_password(password=payload.password)
        )

    async def cancel_qr_login(self) -> QrLoginResponse:
        return QrLoginResponse.model_validate(
            await self.telegram_gateway.cancel_qr_login()
        )

    async def send_auth_code(self, payload: AuthSendCodeRequest) -> dict:
        return await self.telegram_gateway.send_code(phone=payload.phone)

    async def verify_auth_code(self, payload: AuthVerifyCodeRequest) -> dict:
        return await self.telegram_gateway.verify_code(
            code=payload.code,
            phone=payload.phone,
            password=payload.password,
        )

    async def logout(self) -> dict:
        return await self.telegram_gateway.logout()

    async def collect_messages(
        self,
        limit_per_channel: int,
        channel: list[str] | None,
        store: bool,
    ) -> ParseResponse:
        if self.sources_repository.selected_source == "website":
            raise FeatureNotImplementedError(
                "Website parsing is not implemented yet. Select telegram source."
            )

        response = await self.telegram_gateway.parse_configured_channels(
            limit_per_channel=limit_per_channel,
            channels=channel or self.sources_repository.selected_telegram_channels,
        )

        stored_count = None
        if store:
            stored_count = self.messages_repository.store_messages(response.items)

        return response.model_copy(
            update={
                "stored_count": stored_count,
                "storage_backend": "clickhouse" if store else None,
            }
        )
