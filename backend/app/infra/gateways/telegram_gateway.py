from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from urllib.parse import quote, urljoin

import httpx

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # pragma: no cover - optional dependency for local/dev setups
    BeautifulSoup = None

from backend.app.common.schemas import (
    ChannelParseResult,
    MessageSource,
    ParseResponse,
    ParsedMessage,
)
from backend.app.core.config import Settings


class TelegramServiceError(Exception):
    """Raised when public Telegram scraping fails."""


class TelegramGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._public_headers = {
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            )
        }

    @staticmethod
    def _ensure_public_scraping_dependencies() -> None:
        if BeautifulSoup is None:
            raise TelegramServiceError(
                "Telegram public scraping dependency is not installed. Install beautifulsoup4."
            )

    async def parse_configured_channels(
        self,
        *,
        published_after: datetime | None = None,
        channels: list[str] | None = None,
    ) -> ParseResponse:
        self._ensure_public_scraping_dependencies()
        requested_channels = [
            channel_ref.strip()
            for channel_ref in (channels or [])
            if channel_ref and channel_ref.strip()
        ]
        if not requested_channels:
            raise TelegramServiceError("Provide at least one Telegram channel.")

        all_items: list[ParsedMessage] = []
        results: list[ChannelParseResult] = []
        timeout = httpx.Timeout(20.0)

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=self._public_headers,
        ) as client:
            for channel_ref in requested_channels:
                try:
                    normalized_channel = self._normalize_channel_ref(channel_ref)
                    soup = await self._fetch_public_channel_page(
                        client, normalized_channel
                    )
                    channel_title = self._extract_channel_title(
                        soup, normalized_channel
                    )
                    messages = self._parse_public_messages(
                        soup,
                        requested_as=channel_ref,
                        channel_username=normalized_channel,
                        channel_title=channel_title,
                        published_after=published_after,
                    )
                    results.append(
                        ChannelParseResult(
                            requested_as=channel_ref,
                            title=channel_title,
                            username=normalized_channel,
                            status="ok",
                            messages=messages,
                        )
                    )
                    all_items.extend(messages)
                except Exception as exc:
                    results.append(
                        ChannelParseResult(
                            requested_as=channel_ref,
                            status="error",
                            error=str(exc),
                        )
                    )

        all_items.sort(key=lambda item: (item.date, item.id), reverse=True)
        return ParseResponse(
            authorized=True,
            count=len(all_items),
            channels=requested_channels,
            items=all_items,
            results=results,
        )

    async def _fetch_public_channel_page(
        self,
        client: httpx.AsyncClient,
        channel_username: str,
    ) -> BeautifulSoup:
        response = await client.get(f"https://t.me/s/{quote(channel_username)}")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TelegramServiceError(
                f"Telegram returned {response.status_code} for @{channel_username}."
            ) from exc

        soup = BeautifulSoup(response.text, "html.parser")
        if not soup.select(".tgme_widget_message[data-post]"):
            raise TelegramServiceError(
                f"Channel @{channel_username} is unavailable, private, or has no public posts."
            )
        return soup

    def _parse_public_messages(
        self,
        soup: BeautifulSoup,
        *,
        requested_as: str,
        channel_username: str,
        channel_title: str,
        published_after: datetime | None,
    ) -> list[ParsedMessage]:
        messages: list[ParsedMessage] = []
        fallback_channel_id = self._build_public_channel_id(channel_username)

        for node in soup.select(".tgme_widget_message[data-post]"):
            data_post = (node.get("data-post") or "").strip()
            if "/" not in data_post:
                continue

            post_username, raw_message_id = data_post.split("/", maxsplit=1)
            try:
                message_id = int(raw_message_id)
            except ValueError:
                continue

            username = post_username or channel_username
            channel_id = self._build_public_channel_id(username) or fallback_channel_id
            published_at = self._extract_public_datetime(node)
            if published_at is None:
                continue
            if published_after is not None and published_at < published_after:
                continue

            text_block = node.select_one(".tgme_widget_message_text")
            text = text_block.get_text("\n", strip=True) if text_block else ""
            date_link = node.select_one(".tgme_widget_message_date")
            message_url = None
            if date_link is not None and date_link.get("href"):
                message_url = urljoin("https://t.me", str(date_link["href"]))

            views = self._parse_compact_int(
                node.select_one(".tgme_widget_message_views")
            )
            post_author = self._extract_public_author(node)

            messages.append(
                ParsedMessage(
                    message_uid=self._build_message_uid(channel_id, message_id),
                    project_id="default",
                    source_type="telegram",
                    id=message_id,
                    text=text,
                    date=published_at,
                    views=views,
                    forwards=None,
                    post_author=post_author,
                    url=message_url,
                    like_count=None,
                    dislike_count=None,
                    reactions=[],
                    source=MessageSource(
                        channel_id=channel_id,
                        title=channel_title,
                        username=username,
                        requested_as=requested_as,
                    ),
                )
            )

        messages.sort(key=lambda item: (item.date, item.id), reverse=True)
        return messages

    @staticmethod
    def _normalize_channel_ref(channel_ref: str) -> str:
        value = channel_ref.strip()
        for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
            if value.lower().startswith(prefix):
                value = value[len(prefix) :]
                break
        value = value.lstrip("@/")
        if value.startswith("s/"):
            value = value[2:]
        value = value.split("?", maxsplit=1)[0].strip("/")
        if not value:
            raise TelegramServiceError("Telegram channel reference is empty.")
        if value.startswith("+") or value.startswith("joinchat/"):
            raise TelegramServiceError(
                "Private invite links are not supported without a Telegram account."
            )
        return value

    @staticmethod
    def _extract_channel_title(soup: BeautifulSoup, fallback: str) -> str:
        for selector in (
            ".tgme_channel_info_header_title",
            ".tgme_page_title",
        ):
            element = soup.select_one(selector)
            if element is not None:
                title = element.get_text(" ", strip=True)
                if title:
                    return title

        meta = soup.find("meta", attrs={"property": "og:title"})
        if meta is not None:
            title = (meta.get("content") or "").strip()
            if title:
                return title

        return fallback

    @staticmethod
    def _extract_public_datetime(node) -> datetime | None:
        time_node = node.select_one(".tgme_widget_message_date time")
        if time_node is None:
            return None

        raw_value = (
            time_node.get("datetime")
            or time_node.get("title")
            or time_node.get_text(strip=True)
        )
        if not raw_value:
            return None

        normalized = raw_value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    @staticmethod
    def _extract_public_author(node) -> str | None:
        for selector in (
            ".tgme_widget_message_author",
            ".tgme_widget_message_owner_name",
            ".tgme_widget_message_forwarded_from_name",
        ):
            element = node.select_one(selector)
            if element is not None:
                value = element.get_text(" ", strip=True)
                if value:
                    return value
        return None

    @staticmethod
    def _parse_compact_int(node) -> int | None:
        if node is None:
            return None

        raw_value = node.get_text(" ", strip=True).replace("\xa0", "")
        if not raw_value:
            return None

        compact = raw_value.replace(" ", "")
        match = re.fullmatch(r"(?i)(\d+(?:[.,]\d+)?)([KMB])?", compact)
        if match is None:
            digits = re.sub(r"\D", "", compact)
            return int(digits) if digits else None

        number = float(match.group(1).replace(",", "."))
        suffix = (match.group(2) or "").upper()
        multiplier = {
            "": 1,
            "K": 1_000,
            "M": 1_000_000,
            "B": 1_000_000_000,
        }[suffix]
        return int(number * multiplier)

    @staticmethod
    def _build_public_channel_id(channel_username: str) -> int:
        # Public Telegram HTML does not expose a numeric chat id, so we synthesize a stable one.
        digest = hashlib.blake2b(
            channel_username.casefold().encode("utf-8"),
            digest_size=8,
        ).digest()
        return int.from_bytes(digest, byteorder="big", signed=False)

    @staticmethod
    def _build_message_uid(channel_id: int, message_id: int) -> str:
        return f"telegram:{channel_id}:{message_id}"
