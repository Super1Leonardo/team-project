from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse, urlunparse

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - optional for test environments with fake fetchers
    httpx = None
try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # pragma: no cover - optional dependency for local/dev setups
    BeautifulSoup = None

from backend.app.collectors.base import BaseCollector
from backend.app.common.schemas import MessageSource, ParsedMessage
from backend.app.core.exceptions import DomainValidationError


class RssCollector(BaseCollector):
    source_type = "rss"

    def __init__(
        self,
        fetcher: Callable[[str], Awaitable[str]] | None = None,
    ):
        self._fetcher = fetcher or self._fetch

    async def collect(
        self,
        source: dict[str, object],
        *,
        published_after: datetime | None = None,
    ) -> list[ParsedMessage]:
        source_config = source.get("source_config") or {}
        if not isinstance(source_config, dict):
            raise DomainValidationError(
                f"RSS source {source['id']} must contain object source_config."
            )

        feed_url = self._get_feed_url(source_config, source_id=source["id"])
        feed_body = await self._fetcher(feed_url)
        return self._parse_feed(
            feed_url,
            feed_body,
            published_after=published_after,
        )

    async def _fetch(self, feed_url: str) -> str:
        if httpx is None:
            raise RuntimeError("httpx is required to fetch RSS sources.")
        timeout = httpx.Timeout(20.0)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "BrandRadarRSSCollector/1.0"},
        ) as client:
            response = await client.get(feed_url)
            response.raise_for_status()
            return response.text

    @classmethod
    def _get_feed_url(cls, source_config: dict[str, object], *, source_id: object) -> str:
        feed_url = source_config.get("url")
        if not isinstance(feed_url, str) or not feed_url.strip():
            raise DomainValidationError(
                f"RSS source {source_id} must contain source_config.url."
            )

        normalized_url = feed_url.strip()
        parsed = urlparse(normalized_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DomainValidationError(
                f"RSS source {source_id} must contain a valid http(s) source_config.url."
            )
        return normalized_url

    @classmethod
    def _parse_feed(
        cls,
        feed_url: str,
        feed_body: str,
        *,
        published_after: datetime | None,
    ) -> list[ParsedMessage]:
        try:
            root = ET.fromstring(feed_body)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid RSS/Atom XML at {feed_url}.") from exc

        if cls._local_name(root.tag) == "feed":
            items = cls._parse_atom_entries(root, feed_url)
        else:
            items = cls._parse_rss_entries(root, feed_url)

        items.sort(key=lambda item: item.date, reverse=True)
        if published_after is None:
            return items
        return [
            item
            for item in items
            if item.date >= published_after
        ]

    @classmethod
    def _parse_rss_entries(cls, root: ET.Element, feed_url: str) -> list[ParsedMessage]:
        channel = cls._first_child(root, "channel") or root
        feed_title = (
            cls._child_text(channel, "title")
            or urlparse(feed_url).netloc
            or "RSS feed"
        )
        feed_host = urlparse(feed_url).netloc or None
        feed_id = cls._stable_int(feed_url)
        items = cls._children(channel, "item")
        if not items:
            items = cls._children(root, "item")

        return [
            message
            for item in items
            if (message := cls._item_to_message(
                item,
                feed_url=feed_url,
                feed_title=feed_title,
                feed_host=feed_host,
                feed_id=feed_id,
                is_atom=False,
            ))
            is not None
        ]

    @classmethod
    def _parse_atom_entries(cls, root: ET.Element, feed_url: str) -> list[ParsedMessage]:
        feed_title = (
            cls._child_text(root, "title")
            or urlparse(feed_url).netloc
            or "Atom feed"
        )
        feed_host = urlparse(feed_url).netloc or None
        feed_id = cls._stable_int(feed_url)
        entries = cls._children(root, "entry")

        return [
            message
            for entry in entries
            if (message := cls._item_to_message(
                entry,
                feed_url=feed_url,
                feed_title=feed_title,
                feed_host=feed_host,
                feed_id=feed_id,
                is_atom=True,
            ))
            is not None
        ]

    @classmethod
    def _item_to_message(
        cls,
        item: ET.Element,
        *,
        feed_url: str,
        feed_title: str,
        feed_host: str | None,
        feed_id: int,
        is_atom: bool,
    ) -> ParsedMessage | None:
        title = cls._clean_text(cls._child_text(item, "title"))
        text = cls._extract_text(item)
        link = cls._normalize_public_link(
            cls._extract_link(item, is_atom=is_atom),
            feed_url=feed_url,
        )
        author = cls._extract_author(item, is_atom=is_atom)
        external_id = cls._extract_external_id(item, link=link, title=title, feed_url=feed_url)
        published_at = cls._extract_datetime(item)

        if not title and not text and not link:
            return None

        message_uid = f"rss:{feed_id}:{external_id}"
        return ParsedMessage(
            message_uid=message_uid,
            source_type="rss",
            id=cls._stable_int(message_uid),
            title=title,
            text=text or title or link or external_id,
            date=published_at,
            post_author=author,
            url=link,
            meta={
                "external_id": external_id,
                "feed_url": feed_url,
                "feed_host": feed_host,
                "feed_title": feed_title,
                "categories": cls._extract_categories(item),
            },
            source=MessageSource(
                channel_id=feed_id,
                title=feed_title,
                username=feed_host,
                requested_as=feed_url,
            ),
        )

    @classmethod
    def _extract_text(cls, item: ET.Element) -> str:
        for name in ("description", "summary", "content", "encoded"):
            child = cls._first_child(item, name)
            if child is None:
                continue
            raw_text = " ".join(
                part.strip() for part in child.itertext() if part and part.strip()
            )
            cleaned = cls._clean_text(raw_text)
            if cleaned:
                return cleaned
        return ""

    @classmethod
    def _extract_link(cls, item: ET.Element, *, is_atom: bool) -> str | None:
        if is_atom:
            for child in cls._children(item, "link"):
                href = (child.attrib.get("href") or "").strip()
                rel = (child.attrib.get("rel") or "alternate").strip()
                if href and rel in {"alternate", ""}:
                    return href
            return None

        link = cls._child_text(item, "link")
        return link.strip() if link else None

    @staticmethod
    def _normalize_public_link(link: str | None, *, feed_url: str) -> str | None:
        if not link:
            return None

        normalized_link = link.strip()
        parsed_link = urlparse(normalized_link)
        parsed_feed = urlparse(feed_url)

        if not parsed_link.scheme and not parsed_link.netloc:
            return urljoin(f"{parsed_feed.scheme}://{parsed_feed.netloc}", normalized_link)

        if parsed_link.netloc == "rss" and parsed_feed.netloc:
            return urlunparse(
                (
                    parsed_feed.scheme or parsed_link.scheme,
                    parsed_feed.netloc,
                    parsed_link.path,
                    parsed_link.params,
                    parsed_link.query,
                    parsed_link.fragment,
                )
            )

        return normalized_link

    @classmethod
    def _extract_author(cls, item: ET.Element, *, is_atom: bool) -> str | None:
        if is_atom:
            author = cls._first_child(item, "author")
            if author is None:
                return None
            name = cls._child_text(author, "name") or cls._element_text(author)
            return cls._clean_text(name) or None

        author = cls._child_text(item, "author", "creator")
        cleaned = cls._clean_text(author)
        return cleaned or None

    @classmethod
    def _extract_external_id(
        cls,
        item: ET.Element,
        *,
        link: str | None,
        title: str | None,
        feed_url: str,
    ) -> str:
        guid = cls._child_text(item, "guid", "id")
        if guid:
            return guid.strip()
        if link:
            return link
        if title:
            return f"{feed_url}#{title}"
        return f"{feed_url}#{cls._stable_int(ET.tostring(item, encoding='unicode'))}"

    @classmethod
    def _extract_datetime(cls, item: ET.Element) -> datetime:
        for name in ("pubDate", "published", "updated", "date"):
            value = cls._child_text(item, name)
            parsed = cls._parse_datetime(value)
            if parsed is not None:
                return parsed
        return datetime.now(UTC)

    @classmethod
    def _extract_categories(cls, item: ET.Element) -> list[str]:
        categories: list[str] = []
        for child in item:
            if cls._local_name(child.tag) != "category":
                continue
            value = child.attrib.get("term") or cls._element_text(child)
            cleaned = cls._clean_text(value)
            if cleaned:
                categories.append(cleaned)
        return categories

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None

        normalized = value.strip()
        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(normalized)
            except (TypeError, ValueError, IndexError):
                return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _stable_int(value: str) -> int:
        digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
        number = int.from_bytes(digest, byteorder="big", signed=False)
        return max(1, number % (2**63 - 1))

    @staticmethod
    def _clean_text(value: str | None) -> str:
        if not value:
            return ""
        if BeautifulSoup is not None:
            text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
        else:
            try:
                parts = ET.fromstring(f"<root>{value}</root>").itertext()
                text = " ".join(part.strip() for part in parts if part and part.strip())
            except ET.ParseError:
                text = value
        return " ".join(text.split())

    @classmethod
    def _child_text(cls, element: ET.Element, *names: str) -> str | None:
        for child in element:
            if cls._local_name(child.tag) not in names:
                continue
            text = cls._element_text(child)
            if text:
                return text
        return None

    @classmethod
    def _first_child(cls, element: ET.Element, name: str) -> ET.Element | None:
        for child in element:
            if cls._local_name(child.tag) == name:
                return child
        return None

    @classmethod
    def _children(cls, element: ET.Element, name: str) -> list[ET.Element]:
        return [child for child in element if cls._local_name(child.tag) == name]

    @staticmethod
    def _element_text(element: ET.Element) -> str | None:
        text = " ".join(part.strip() for part in element.itertext() if part and part.strip())
        return text or None

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]
