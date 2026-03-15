from backend.app.core.exceptions import FeatureNotImplementedError
from backend.app.infra.gateways.telegram_gateway import TelegramGateway
from backend.app.modules.collector.schemas import ParseResponse
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
