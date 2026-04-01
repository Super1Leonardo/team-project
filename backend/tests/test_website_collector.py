from __future__ import annotations

import unittest
from datetime import UTC, datetime

from backend.app.collectors.website import BeautifulSoup, WebsiteCollector
from backend.app.core.exceptions import DomainValidationError


INDEX_HTML = """\
<!doctype html>
<html lang="ru">
<head>
  <title>Test Website</title>
</head>
<body>
  <h1>Test Website</h1>
  <article>
    <h2><a href="/post/older-post">Older post</a></h2>
    <div class="meta">Опубликовано: 2026-03-14T10:00:00+00:00</div>
    <p>Older preview</p>
  </article>
  <article>
    <h2><a href="/post/newer-post">Newer post</a></h2>
    <div class="meta">Опубликовано: 2026-03-15T12:30:00+00:00</div>
    <p>Newer preview</p>
  </article>
</body>
</html>
"""


DETAIL_NEWER_HTML = """\
<!doctype html>
<html lang="ru">
<body>
  <p><a href="/">Назад</a></p>
  <h1>Newer post</h1>
  <div class="meta">ID: newer-post</div>
  <p>Full newer text with details.</p>
  <p><a href="https://origin.example.com/newer-post" target="_blank">Оригинал</a></p>
</body>
</html>
"""


DETAIL_OLDER_HTML = """\
<!doctype html>
<html lang="ru">
<body>
  <h1>Older post</h1>
  <p>Full older text.</p>
</body>
</html>
"""


class _FakeWebsiteResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _FakeWebsiteAsyncClient:
    def __init__(self, bodies: dict[str, str]) -> None:
        self.bodies = bodies
        self.requested_urls: list[str] = []
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(self) -> "_FakeWebsiteAsyncClient":
        self.enter_count += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exit_count += 1
        return None

    async def get(self, url: str) -> _FakeWebsiteResponse:
        self.requested_urls.append(url)
        body = self.bodies.get(url)
        if body is None:
            raise AssertionError(f"Unexpected URL requested: {url}")
        return _FakeWebsiteResponse(body)


@unittest.skipIf(BeautifulSoup is None, "beautifulsoup4 is not installed in the test environment")
class WebsiteCollectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_collect_parses_articles_and_filters_by_published_after(self) -> None:
        async def fake_fetcher(url: str) -> str:
            if url == "https://example.com/news":
                return INDEX_HTML
            if url == "https://example.com/post/newer-post":
                return DETAIL_NEWER_HTML
            if url == "https://example.com/post/older-post":
                return DETAIL_OLDER_HTML
            raise AssertionError(f"Unexpected URL requested: {url}")

        collector = WebsiteCollector(fetcher=fake_fetcher)
        source = {"id": 25, "source_config": {"url": "https://example.com/news"}}
        published_after = datetime(2026, 3, 15, 0, 0, tzinfo=UTC)

        items = await collector.collect(source, published_after=published_after)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.source_type, "website")
        self.assertEqual(item.title, "Newer post")
        self.assertEqual(item.text, "Full newer text with details.")
        self.assertEqual(item.url, "https://example.com/post/newer-post")
        self.assertEqual(item.meta["external_id"], "newer-post")
        self.assertEqual(item.meta["detail_url"], "https://example.com/post/newer-post")
        self.assertEqual(item.source.requested_as, "https://example.com/news")
        self.assertEqual(item.source.title, "Test Website")

    async def test_collect_stores_original_url_when_present(self) -> None:
        async def fake_fetcher(url: str) -> str:
            if url == "https://example.com/news":
                return INDEX_HTML
            if url == "https://example.com/post/older-post":
                return DETAIL_OLDER_HTML
            if url == "https://example.com/post/newer-post":
                return DETAIL_NEWER_HTML
            raise AssertionError(f"Unexpected URL requested: {url}")

        collector = WebsiteCollector(fetcher=fake_fetcher)
        source = {"id": 26, "source_config": {"url": "https://example.com/news"}}

        items = await collector.collect(source)

        self.assertEqual(len(items), 2)
        newer_item = next(item for item in items if item.meta["external_id"] == "newer-post")
        self.assertEqual(
            newer_item.meta["original_url"],
            "https://origin.example.com/newer-post",
        )
        self.assertEqual(newer_item.text, "Full newer text with details.")

    async def test_collect_reuses_one_http_client_for_index_and_detail_pages(self) -> None:
        collector = WebsiteCollector()
        fake_client = _FakeWebsiteAsyncClient(
            {
                "https://example.com/news": INDEX_HTML,
                "https://example.com/post/older-post": DETAIL_OLDER_HTML,
                "https://example.com/post/newer-post": DETAIL_NEWER_HTML,
            }
        )
        collector._build_client = lambda: fake_client  # type: ignore[method-assign]
        source = {"id": 28, "source_config": {"url": "https://example.com/news"}}

        items = await collector.collect(source)

        self.assertEqual(len(items), 2)
        self.assertEqual(fake_client.enter_count, 1)
        self.assertEqual(fake_client.exit_count, 1)
        self.assertEqual(fake_client.requested_urls[0], "https://example.com/news")
        self.assertEqual(
            set(fake_client.requested_urls[1:]),
            {
                "https://example.com/post/older-post",
                "https://example.com/post/newer-post",
            },
        )

    async def test_collect_requires_valid_website_url(self) -> None:
        async def fake_fetcher(_: str) -> str:
            return INDEX_HTML

        collector = WebsiteCollector(fetcher=fake_fetcher)
        source = {"id": 27, "source_config": {"url": "ftp://example.com/news"}}

        with self.assertRaises(DomainValidationError):
            await collector.collect(source)
