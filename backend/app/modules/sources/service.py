from backend.app.core.config import Settings
from backend.app.core.exceptions import DomainValidationError
from backend.app.modules.sources.repository import ParserSettingsRepository
from backend.app.modules.sources.schemas import (
    AppConfigResponse,
    AuthMethodsResponse,
    RssFeedsResponse,
    RssFeedsSelectionRequest,
    SourceSelectionRequest,
    SourceSelectionResponse,
    TelegramChannelsResponse,
    TelegramChannelsSelectionRequest,
)


class SourcesService:
    def __init__(self, repository: ParserSettingsRepository, settings: Settings):
        self.repository = repository
        self.settings = settings

    def get_app_config(self) -> AppConfigResponse:
        return AppConfigResponse(
            api_title=self.settings.api_title,
            api_version=self.settings.api_version,
            selected_source=self.repository.selected_source,
            selected_channels=self.repository.selected_telegram_channels,
            available_channels=self.repository.available_telegram_channels,
            selected_rss_feeds=self.repository.selected_rss_feeds,
            available_rss_feeds=self.repository.available_rss_feeds,
            available_sources=self.repository.get_source_selection()["sources"],
            auth_methods=AuthMethodsResponse(code=False, qr=False),
            docs_url="/docs",
            health_url="/api/health",
        )

    def get_source_selection(self) -> SourceSelectionResponse:
        return SourceSelectionResponse.model_validate(
            self.repository.get_source_selection()
        )

    def set_source_selection(
        self,
        payload: SourceSelectionRequest,
    ) -> SourceSelectionResponse:
        try:
            return SourceSelectionResponse.model_validate(
                self.repository.set_source(payload.source)
            )
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc

    def get_telegram_channels(self) -> TelegramChannelsResponse:
        return TelegramChannelsResponse.model_validate(
            self.repository.get_telegram_channels()
        )

    def set_telegram_channels(
        self,
        payload: TelegramChannelsSelectionRequest,
    ) -> TelegramChannelsResponse:
        try:
            return TelegramChannelsResponse.model_validate(
                self.repository.set_telegram_channels(payload.channels)
            )
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc

    def get_rss_feeds(self) -> RssFeedsResponse:
        return RssFeedsResponse.model_validate(
            self.repository.get_rss_feeds()
        )

    def set_rss_feeds(
        self,
        payload: RssFeedsSelectionRequest,
    ) -> RssFeedsResponse:
        try:
            return RssFeedsResponse.model_validate(
                self.repository.set_rss_feeds(payload.feeds)
            )
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc
