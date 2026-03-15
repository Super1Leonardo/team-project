from backend.app.core.exceptions import DomainValidationError, FeatureNotImplementedError
from backend.app.collectors.rss import RssCollector
from backend.app.infra.gateways.telegram_gateway import TelegramGateway
from backend.app.common.schemas import ChannelParseResult, ParseResponse
from backend.app.modules.messages.repository import MessagesRepository
from backend.app.modules.sources.repository import ParserSettingsRepository


class CollectorService:
    def __init__(
        self,
        telegram_gateway: TelegramGateway,
        rss_collector: RssCollector,
        sources_repository: ParserSettingsRepository,
        messages_repository: MessagesRepository,
    ):
        self.telegram_gateway = telegram_gateway
        self.rss_collector = rss_collector
        self.sources_repository = sources_repository
        self.messages_repository = messages_repository

    async def collect_messages(
        self,
        limit_per_channel: int,
        channel: list[str] | None,
        store: bool,
    ) -> ParseResponse:
        selected_source = self.sources_repository.selected_source
        if selected_source == "website":
            raise FeatureNotImplementedError(
                "Website parsing is not implemented yet. Select telegram source."
            )

        if selected_source == "rss":
            response = await self._collect_rss_messages(
                limit_per_feed=limit_per_channel,
                feeds=channel or self.sources_repository.selected_rss_feeds,
            )
        else:
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

    async def _collect_rss_messages(
        self,
        *,
        limit_per_feed: int,
        feeds: list[str],
    ) -> ParseResponse:
        items = []
        results: list[ChannelParseResult] = []
        requested_feeds = list(feeds)
        if not requested_feeds:
            raise DomainValidationError(
                "Choose at least one RSS feed before running the parser."
            )

        for index, feed_url in enumerate(requested_feeds, start=1):
            source = {
                "id": index,
                "source_config": {"url": feed_url},
            }
            try:
                feed_items = await self.rss_collector.collect(source, limit=limit_per_feed)
            except Exception as exc:
                results.append(
                    ChannelParseResult(
                        requested_as=feed_url,
                        status="error",
                        error=str(exc),
                        messages=[],
                    )
                )
                continue

            items.extend(feed_items)
            first_message = feed_items[0] if feed_items else None
            results.append(
                ChannelParseResult(
                    requested_as=feed_url,
                    title=first_message.source.title if first_message else None,
                    username=first_message.source.username if first_message else None,
                    status="ok",
                    messages=feed_items,
                )
            )

        return ParseResponse(
            authorized=True,
            count=len(items),
            channels=requested_feeds,
            items=items,
            results=results,
        )
