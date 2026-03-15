from __future__ import annotations

import unittest

from backend.app.collectors.rss import RssCollector
from backend.app.core.exceptions import DomainValidationError


RSS_SAMPLE = """\
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>BrandRadar Feed</title>
    <item>
      <title>Older post</title>
      <link>https://example.com/posts/1</link>
      <guid>post-1</guid>
      <description><![CDATA[<p>Older <b>news</b></p>]]></description>
      <pubDate>Sun, 14 Mar 2026 10:00:00 GMT</pubDate>
      <dc:creator>Editor One</dc:creator>
      <category>News</category>
    </item>
    <item>
      <title>Newer post</title>
      <link>https://example.com/posts/2</link>
      <guid>post-2</guid>
      <description><![CDATA[<p>Fresh <i>update</i></p>]]></description>
      <pubDate>Sun, 14 Mar 2026 12:30:00 GMT</pubDate>
      <dc:creator>Editor Two</dc:creator>
      <category>Updates</category>
    </item>
  </channel>
</rss>
"""


class RssCollectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_collect_parses_feed_items_and_limits_results(self) -> None:
        async def fake_fetcher(_: str) -> str:
            return RSS_SAMPLE

        collector = RssCollector(fetcher=fake_fetcher)
        source = {"id": 17, "source_config": {"url": "https://example.com/feed.xml"}}

        items = await collector.collect(source, limit=1)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.source_type, "rss")
        self.assertEqual(item.title, "Newer post")
        self.assertEqual(item.text, "Fresh update")
        self.assertEqual(item.post_author, "Editor Two")
        self.assertEqual(item.url, "https://example.com/posts/2")
        self.assertEqual(item.meta["external_id"], "post-2")
        self.assertEqual(item.meta["categories"], ["Updates"])
        self.assertEqual(item.source.requested_as, "https://example.com/feed.xml")
        self.assertEqual(item.source.title, "BrandRadar Feed")

    async def test_collect_requires_valid_feed_url(self) -> None:
        async def fake_fetcher(_: str) -> str:
            return RSS_SAMPLE

        collector = RssCollector(fetcher=fake_fetcher)
        source = {"id": 18, "source_config": {"url": "ftp://example.com/feed.xml"}}

        with self.assertRaises(DomainValidationError):
            await collector.collect(source)
