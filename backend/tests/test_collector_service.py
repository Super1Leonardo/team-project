from __future__ import annotations

import unittest
from datetime import UTC, datetime

from backend.app.common.schemas import MessageSource, ParsedMessage
from backend.app.core.exceptions import DomainValidationError
from backend.app.modules.collector.service import CollectorService


class _FakeTelegramGateway:
    async def parse_configured_channels(self, *, limit_per_channel: int, channels: list[str]):
        raise AssertionError("Telegram gateway must not be used for RSS selection.")


class _FakeRssCollector:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def collect(self, source: dict, *, limit: int = 100):
        self.calls.append({"source": source, "limit": limit})
        published_at = datetime.now(UTC)
        return [
            ParsedMessage(
                message_uid="rss:1:post-1",
                source_type="rss",
                id=1,
                title="RSS title",
                text="RSS body",
                date=published_at,
                url="https://example.com/posts/1",
                source=MessageSource(
                    channel_id=1,
                    title="Example Feed",
                    username="example.com",
                    requested_as=source["source_config"]["url"],
                ),
            )
        ]


class _FakeSourcesRepository:
    def __init__(self, selected_rss_feeds: list[str] | None = None) -> None:
        self.selected_source = "rss"
        if selected_rss_feeds is None:
            selected_rss_feeds = ["https://example.com/feed.xml"]
        self.selected_rss_feeds = selected_rss_feeds


class _FakeMessagesRepository:
    def __init__(self) -> None:
        self.saved_items: list[ParsedMessage] = []

    def store_messages(self, items: list[ParsedMessage]) -> int:
        self.saved_items.extend(items)
        return len(items)


class CollectorServiceRssTests(unittest.IsolatedAsyncioTestCase):
    async def test_collect_messages_uses_rss_collector_and_stores_results(self) -> None:
        rss_collector = _FakeRssCollector()
        messages_repository = _FakeMessagesRepository()
        service = CollectorService(
            telegram_gateway=_FakeTelegramGateway(),
            rss_collector=rss_collector,
            sources_repository=_FakeSourcesRepository(),
            messages_repository=messages_repository,
        )

        response = await service.collect_messages(
            limit_per_channel=5,
            channel=None,
            store=True,
        )

        self.assertEqual(response.count, 1)
        self.assertEqual(response.channels, ["https://example.com/feed.xml"])
        self.assertEqual(response.storage_backend, "clickhouse")
        self.assertEqual(response.stored_count, 1)
        self.assertEqual(response.items[0].source_type, "rss")
        self.assertEqual(
            rss_collector.calls[0]["source"]["source_config"]["url"],
            "https://example.com/feed.xml",
        )
        self.assertEqual(len(messages_repository.saved_items), 1)

    async def test_collect_messages_requires_configured_rss_feeds(self) -> None:
        service = CollectorService(
            telegram_gateway=_FakeTelegramGateway(),
            rss_collector=_FakeRssCollector(),
            sources_repository=_FakeSourcesRepository(selected_rss_feeds=[]),
            messages_repository=_FakeMessagesRepository(),
        )

        with self.assertRaises(DomainValidationError):
            await service.collect_messages(
                limit_per_channel=5,
                channel=None,
                store=False,
            )
