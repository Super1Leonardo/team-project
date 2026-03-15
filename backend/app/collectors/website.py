from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - optional for test environments with fake fetchers
    httpx = None
from bs4 import BeautifulSoup, Tag

from backend.app.collectors.base import BaseCollector
from backend.app.common.schemas import MessageSource, ParsedMessage
from backend.app.core.exceptions import DomainValidationError


class WebsiteCollector(BaseCollector):
    source_type = "website"

    _DEFAULT_SELECTORS = {
        "article_selector": "article",
        "link_selector": "h2 a",
        "summary_selector": "p",
        "date_selector": ".meta",
        "site_title_selector": "h1",
        "detail_title_selector": "h1",
        "detail_paragraph_selector": "body > p",
        "original_link_selector": 'a[target="_blank"]',
    }

    def __init__(
        self,
        fetcher: Callable[[str], Awaitable[str]] | None = None,
        *,
        detail_concurrency: int = 5,
    ):
        self._fetcher = fetcher or self._fetch
        self._detail_concurrency = max(1, detail_concurrency)

    async def collect(
        self,
        source: dict[str, Any],
        *,
        limit: int = 100,
    ) -> list[ParsedMessage]:
        source_config = source.get("source_config") or {}
        if not isinstance(source_config, dict):
            raise DomainValidationError(
                f"Website source {source['id']} must contain object source_config."
            )

        base_url = self._get_source_url(source_config, source_id=source["id"])
        selectors = self._resolve_selectors(source_config, source_id=source["id"])
        index_body = await self._fetcher(base_url)
        site_title, entries = self._parse_index_page(base_url, index_body, selectors)
        unique_entries = self._deduplicate_entries(entries, limit=limit)
        if not unique_entries:
            return []

        return await self._hydrate_entries(
            base_url=base_url,
            site_title=site_title,
            entries=unique_entries,
            selectors=selectors,
        )

    async def _fetch(self, url: str) -> str:
        if httpx is None:
            raise RuntimeError("httpx is required to fetch website sources.")
        timeout = httpx.Timeout(20.0)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "BrandRadarWebsiteCollector/1.0"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    @classmethod
    def _get_source_url(cls, source_config: dict[str, Any], *, source_id: object) -> str:
        raw_url = source_config.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise DomainValidationError(
                f"Website source {source_id} must contain source_config.url."
            )

        normalized_url = raw_url.strip()
        parsed = urlparse(normalized_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise DomainValidationError(
                f"Website source {source_id} must contain a valid http(s) source_config.url."
            )
        return normalized_url

    @classmethod
    def _resolve_selectors(
        cls,
        source_config: dict[str, Any],
        *,
        source_id: object,
    ) -> dict[str, str]:
        selectors = dict(cls._DEFAULT_SELECTORS)
        for key in selectors:
            if key not in source_config:
                continue
            value = source_config[key]
            if not isinstance(value, str) or not value.strip():
                raise DomainValidationError(
                    f"Website source {source_id} must contain non-empty source_config.{key}."
                )
            selectors[key] = value.strip()
        return selectors

    @classmethod
    def _parse_index_page(
        cls,
        base_url: str,
        html: str,
        selectors: dict[str, str],
    ) -> tuple[str, list[dict[str, Any]]]:
        soup = BeautifulSoup(html, "html.parser")
        site_title = cls._extract_site_title(soup, base_url, selectors)
        article_nodes = soup.select(selectors["article_selector"])
        entries: list[dict[str, Any]] = []

        for article in article_nodes:
            link = article.select_one(selectors["link_selector"])
            if not isinstance(link, Tag):
                continue

            href = (link.get("href") or "").strip()
            if not href:
                continue

            detail_url = urljoin(base_url, href)
            external_id = cls._extract_external_id(detail_url)
            title = cls._clean_text(link.get_text(" ", strip=True))
            summary = cls._extract_summary(article, selectors["summary_selector"])
            published_at = cls._extract_published_at(article, selectors["date_selector"])

            entries.append(
                {
                    "external_id": external_id,
                    "detail_url": detail_url,
                    "title": title or external_id,
                    "summary": summary,
                    "published_at": published_at,
                }
            )

        return site_title, entries

    @classmethod
    def _deduplicate_entries(
        cls,
        entries: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        unique_entries: list[dict[str, Any]] = []
        seen_external_ids: set[str] = set()

        for entry in entries:
            external_id = entry["external_id"]
            if external_id in seen_external_ids:
                continue
            seen_external_ids.add(external_id)
            unique_entries.append(entry)
            if len(unique_entries) >= limit:
                break

        return unique_entries

    async def _hydrate_entries(
        self,
        *,
        base_url: str,
        site_title: str,
        entries: list[dict[str, Any]],
        selectors: dict[str, str],
    ) -> list[ParsedMessage]:
        semaphore = asyncio.Semaphore(self._detail_concurrency)
        site_id = self._stable_int(base_url)
        parsed_base_url = urlparse(base_url)
        source_username = parsed_base_url.netloc or None

        async def hydrate(entry: dict[str, Any]) -> ParsedMessage:
            async with semaphore:
                detail_payload = await self._load_detail_page(
                    detail_url=entry["detail_url"],
                    selectors=selectors,
                )

            detail_title = detail_payload["title"] or entry["title"]
            detail_text = detail_payload["text"] or entry["summary"] or detail_title
            message_uid = f"website:{site_id}:{entry['external_id']}"

            meta = {
                "external_id": entry["external_id"],
                "detail_url": entry["detail_url"],
                "site_url": base_url,
                "site_title": site_title,
            }
            if detail_payload["original_url"]:
                meta["original_url"] = detail_payload["original_url"]
            if entry["summary"]:
                meta["summary"] = entry["summary"]

            return ParsedMessage(
                message_uid=message_uid,
                source_type="website",
                id=self._stable_int(message_uid),
                title=detail_title,
                text=detail_text,
                date=entry["published_at"],
                url=entry["detail_url"],
                meta=meta,
                source=MessageSource(
                    channel_id=site_id,
                    title=site_title,
                    username=source_username,
                    requested_as=base_url,
                ),
            )

        return await asyncio.gather(*(hydrate(entry) for entry in entries))

    async def _load_detail_page(
        self,
        *,
        detail_url: str,
        selectors: dict[str, str],
    ) -> dict[str, str]:
        try:
            detail_body = await self._fetcher(detail_url)
        except Exception:
            return {
                "title": "",
                "text": "",
                "original_url": "",
            }

        soup = BeautifulSoup(detail_body, "html.parser")
        return {
            "title": self._extract_detail_title(soup, selectors["detail_title_selector"]),
            "text": self._extract_detail_text(soup, selectors["detail_paragraph_selector"]),
            "original_url": self._extract_original_url(
                soup,
                detail_url,
                selectors["original_link_selector"],
            ),
        }

    @classmethod
    def _extract_site_title(
        cls,
        soup: BeautifulSoup,
        base_url: str,
        selectors: dict[str, str],
    ) -> str:
        title_node = soup.select_one(selectors["site_title_selector"]) or soup.find("title")
        if isinstance(title_node, Tag):
            cleaned = cls._clean_text(title_node.get_text(" ", strip=True))
            if cleaned:
                return cleaned
        return urlparse(base_url).netloc or "Website"

    @classmethod
    def _extract_summary(cls, article: Tag, summary_selector: str) -> str:
        for node in article.select(summary_selector):
            if not isinstance(node, Tag):
                continue
            text = cls._clean_text(node.get_text(" ", strip=True))
            if text:
                return text
        return ""

    @classmethod
    def _extract_published_at(cls, article: Tag, date_selector: str) -> datetime:
        for node in article.select(date_selector):
            if not isinstance(node, Tag):
                continue
            raw_text = cls._clean_text(node.get_text(" ", strip=True))
            if not raw_text:
                continue
            normalized = raw_text.removeprefix("Опубликовано:").strip()
            parsed = cls._parse_datetime(normalized)
            if parsed is not None:
                return parsed
        return datetime.now(UTC)

    @classmethod
    def _extract_detail_title(cls, soup: BeautifulSoup, selector: str) -> str:
        node = soup.select_one(selector)
        if not isinstance(node, Tag):
            return ""
        return cls._clean_text(node.get_text(" ", strip=True))

    @classmethod
    def _extract_detail_text(cls, soup: BeautifulSoup, selector: str) -> str:
        candidates: list[str] = []

        for node in soup.select(selector):
            if not isinstance(node, Tag):
                continue
            text = cls._clean_text(node.get_text("\n", strip=True))
            if not text:
                continue

            link_only = cls._is_link_only_paragraph(node, text)
            if link_only:
                continue

            candidates.append(text)

        if not candidates:
            return ""
        return max(candidates, key=len)

    @classmethod
    def _extract_original_url(
        cls,
        soup: BeautifulSoup,
        detail_url: str,
        selector: str,
    ) -> str:
        node = soup.select_one(selector)
        if not isinstance(node, Tag):
            return ""

        href = (node.get("href") or "").strip()
        if not href:
            return ""
        return urljoin(detail_url, href)

    @classmethod
    def _is_link_only_paragraph(cls, node: Tag, text: str) -> bool:
        links = node.find_all("a")
        if not links:
            return False

        link_text = cls._clean_text(" ".join(link.get_text(" ", strip=True) for link in links))
        if not link_text:
            return False
        return text == link_text

    @staticmethod
    def _extract_external_id(detail_url: str) -> str:
        clean_url = urldefrag(detail_url).url.rstrip("/")
        parsed = urlparse(clean_url)
        if parsed.path:
            return parsed.path.rsplit("/", 1)[-1] or parsed.path
        return clean_url

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
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
        return " ".join(value.split())
