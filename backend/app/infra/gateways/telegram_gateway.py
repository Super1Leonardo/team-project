from __future__ import annotations

import asyncio
import base64
import hashlib
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import quote, urljoin

import httpx
try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # pragma: no cover - optional dependency for local/dev setups
    BeautifulSoup = None

try:
    import qrcode
    from qrcode.image.svg import SvgPathImage
except (
    ModuleNotFoundError
):  # pragma: no cover - optional dependency for local/dev setups
    qrcode = None
    SvgPathImage = None

try:
    from telethon import TelegramClient
    from telethon.errors import (
        ApiIdInvalidError,
        PhoneCodeExpiredError,
        PhoneCodeInvalidError,
        PhoneNumberInvalidError,
        SessionPasswordNeededError,
    )
    from telethon.tl.types import ReactionCustomEmoji, ReactionEmoji
except (
    ModuleNotFoundError
):  # pragma: no cover - optional dependency for local/dev setups
    TelegramClient = None

    class ApiIdInvalidError(Exception):
        pass

    class PhoneCodeExpiredError(Exception):
        pass

    class PhoneCodeInvalidError(Exception):
        pass

    class PhoneNumberInvalidError(Exception):
        pass

    class SessionPasswordNeededError(Exception):
        pass

    class ReactionCustomEmoji:  # type: ignore[no-redef]
        pass

    class ReactionEmoji:  # type: ignore[no-redef]
        pass


from backend.app.common.schemas import (
    AuthStatusResponse,
    ChannelParseResult,
    MessageSource,
    ParseResponse,
    ParsedMessage,
    UserInfo,
)
from backend.app.core.config import Settings
from backend.app.modules.sources.constants import TARGET_CHANNELS


class TelegramServiceError(Exception):
    """Raised when public Telegram scraping fails."""


class TelegramConfigurationError(TelegramServiceError):
    """Raised when required Telegram credentials are missing."""


class TelegramUnauthorizedError(TelegramServiceError):
    """Raised when the Telegram session is not authorized."""


class TelegramPasswordRequiredError(TelegramServiceError):
    """Raised when Telegram account has 2FA password enabled."""


class TelegramCodeNotRequestedError(TelegramServiceError):
    """Raised when verify is called before requesting a code."""


@dataclass
class PendingCode:
    phone: str
    phone_code_hash: str
    requested_at: datetime


@dataclass
class PendingQrLogin:
    client: TelegramClient
    qr_login: object
    created_at: datetime
    expires_at: datetime
    wait_task: asyncio.Task | None = None
    status: str = "pending"
    error: str | None = None
    user: UserInfo | None = None


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
        self._pending_codes: dict[str, PendingCode] = {}
        self._pending_qr: PendingQrLogin | None = None
        self._qr_lock = asyncio.Lock()

    def _ensure_credentials(self) -> None:
        self._ensure_runtime_dependencies()
        if not self.settings.credentials_configured:
            raise TelegramConfigurationError(
                "Set TELEGRAM_API_ID and TELEGRAM_API_HASH before using the parser."
            )

    @staticmethod
    def _ensure_runtime_dependencies() -> None:
        if TelegramClient is None or qrcode is None or SvgPathImage is None:
            raise TelegramConfigurationError(
                "Telegram integration dependencies are not installed. "
                "Install telethon and qrcode to use Telegram auth and collection."
            )

    @staticmethod
    def _ensure_public_scraping_dependencies() -> None:
        if BeautifulSoup is None:
            raise TelegramServiceError(
                "Telegram public scraping dependency is not installed. Install beautifulsoup4."
            )

    def _new_client(self) -> TelegramClient:
        self._ensure_credentials()
        return TelegramClient(
            str(self.settings.telegram_session_path),
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
        )

    @asynccontextmanager
    async def _client(self):
        client = self._new_client()
        await client.connect()
        try:
            yield client
        finally:
            await client.disconnect()

    async def get_auth_status(
        self,
        selected_channels: list[str] | None = None,
    ) -> AuthStatusResponse:
        channels = selected_channels or TARGET_CHANNELS
        if not self.settings.credentials_configured:
            return AuthStatusResponse(
                configured=False,
                authorized=False,
                phone_hint=self.settings.telegram_phone,
                user=None,
                selected_channels=channels,
            )

        pending = self._pending_qr
        if pending and pending.status in {"pending", "password_required"}:
            return AuthStatusResponse(
                configured=True,
                authorized=False,
                phone_hint=self.settings.telegram_phone,
                user=None,
                selected_channels=channels,
            )

        if pending and pending.status == "authorized" and pending.user:
            return AuthStatusResponse(
                configured=True,
                authorized=True,
                phone_hint=self.settings.telegram_phone,
                user=pending.user,
                selected_channels=channels,
            )

        async with self._client() as client:
            authorized = await client.is_user_authorized()
            user = None
            if authorized:
                me = await client.get_me()
                user = self._user_to_model(me)

            return AuthStatusResponse(
                configured=True,
                authorized=authorized,
                phone_hint=self.settings.telegram_phone,
                user=user,
                selected_channels=channels,
            )

    async def start_qr_login(self, recreate: bool = False) -> dict:
        async with self._qr_lock:
            pending = self._pending_qr
            if (
                pending
                and pending.status in {"pending", "password_required"}
                and not recreate
            ):
                return self._serialize_qr_state(pending)

            await self._clear_pending_qr()

            client = self._new_client()
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                await client.disconnect()
                return {
                    "authorized": True,
                    "status": "authorized",
                    "message": "Session is already authorized.",
                    "user": self._user_to_model(me).model_dump(),
                    "qr_url": None,
                    "qr_image_data_url": None,
                    "expires_at": None,
                    "error": None,
                    "next_step": "You can load messages now.",
                }

            qr_login = await client.qr_login()
            pending = PendingQrLogin(
                client=client,
                qr_login=qr_login,
                created_at=datetime.now(UTC),
                expires_at=qr_login.expires,
            )
            pending.wait_task = asyncio.create_task(self._wait_for_qr_login(pending))
            self._pending_qr = pending
            return self._serialize_qr_state(pending)

    async def get_qr_login_status(self) -> dict:
        async with self._qr_lock:
            pending = self._pending_qr
            if pending is None:
                auth_status = await self.get_auth_status()
                if auth_status.authorized:
                    return {
                        "authorized": True,
                        "status": "authorized",
                        "message": "Session is already authorized.",
                        "user": auth_status.user.model_dump()
                        if auth_status.user
                        else None,
                        "qr_url": None,
                        "qr_image_data_url": None,
                        "expires_at": None,
                        "error": None,
                        "next_step": "You can load messages now.",
                    }

                return {
                    "authorized": False,
                    "status": "idle",
                    "message": "Generate a QR code to log in.",
                    "user": None,
                    "qr_url": None,
                    "qr_image_data_url": None,
                    "expires_at": None,
                    "error": None,
                    "next_step": "Open Telegram on another authorized device and scan the QR code.",
                }

            return self._serialize_qr_state(pending)

    async def verify_qr_password(self, password: str) -> dict:
        async with self._qr_lock:
            pending = self._pending_qr
            if pending is None or pending.status != "password_required":
                raise TelegramServiceError(
                    "QR login is not waiting for a 2FA password."
                )

            try:
                await pending.client.sign_in(password=password)
                me = await pending.client.get_me()
                pending.user = self._user_to_model(me)
                pending.status = "authorized"
                pending.error = None
                return self._serialize_qr_state(pending)
            finally:
                await self._disconnect_client(pending.client)

    async def cancel_qr_login(self) -> dict:
        async with self._qr_lock:
            await self._clear_pending_qr()
            return {
                "authorized": False,
                "status": "idle",
                "message": "QR login cancelled.",
                "user": None,
                "qr_url": None,
                "qr_image_data_url": None,
                "expires_at": None,
                "error": None,
                "next_step": "Generate a fresh QR code to continue.",
            }

    async def send_code(self, phone: str | None = None) -> dict:
        phone_value = phone or self.settings.telegram_phone
        if not phone_value:
            raise TelegramConfigurationError(
                "Phone number is required. Pass it in the request body or set TELEGRAM_PHONE."
            )

        try:
            async with self._client() as client:
                if await client.is_user_authorized():
                    me = await client.get_me()
                    return {
                        "authorized": True,
                        "message": "Session is already authorized.",
                        "user": self._user_to_model(me).model_dump(),
                    }

                sent_code = await client.send_code_request(phone_value)
                delivery = self._serialize_sent_code(sent_code)
                self._pending_codes[phone_value] = PendingCode(
                    phone=phone_value,
                    phone_code_hash=sent_code.phone_code_hash,
                    requested_at=datetime.now(UTC),
                )
                return {
                    "authorized": False,
                    "phone": phone_value,
                    "message": (
                        "Telegram login code requested."
                        if not delivery["delivery_type"]
                        else f"Telegram login code requested via {delivery['delivery_type']}."
                    ),
                    "requested_at": self._pending_codes[
                        phone_value
                    ].requested_at.isoformat(),
                    **delivery,
                }
        except PhoneNumberInvalidError as exc:
            raise TelegramServiceError(
                "Invalid phone number format for Telegram."
            ) from exc
        except ApiIdInvalidError as exc:
            raise TelegramConfigurationError(
                "Invalid TELEGRAM_API_ID or TELEGRAM_API_HASH."
            ) from exc

    async def verify_code(
        self,
        code: str,
        phone: str | None = None,
        password: str | None = None,
    ) -> dict:
        phone_value = phone or self.settings.telegram_phone
        if not phone_value:
            raise TelegramConfigurationError(
                "Phone number is required. Pass it in the request body or set TELEGRAM_PHONE."
            )

        pending = self._pending_codes.get(phone_value)
        if pending is None:
            raise TelegramCodeNotRequestedError(
                "Login code was not requested for this phone. Call /api/telegram/auth/send-code first."
            )

        async with self._client() as client:
            try:
                await client.sign_in(
                    phone=phone_value,
                    code=code,
                    phone_code_hash=pending.phone_code_hash,
                )
            except SessionPasswordNeededError as exc:
                if not password:
                    raise TelegramPasswordRequiredError(
                        "This account requires a 2FA password. Send it in the password field."
                    ) from exc
                await client.sign_in(password=password)
            except PhoneCodeInvalidError as exc:
                raise TelegramServiceError("Invalid Telegram login code.") from exc
            except PhoneCodeExpiredError as exc:
                raise TelegramServiceError(
                    "Telegram login code expired. Request a new code."
                ) from exc

            self._pending_codes.pop(phone_value, None)
            me = await client.get_me()
            return {
                "authorized": True,
                "message": "Telegram session authorized.",
                "user": self._user_to_model(me).model_dump(),
            }

    async def parse_configured_channels(
        self,
        limit_per_channel: int = 20,
        channels: list[str] | None = None,
    ) -> ParseResponse:
        self._ensure_public_scraping_dependencies()
        requested_channels = channels or TARGET_CHANNELS
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
                        limit_per_channel=limit_per_channel,
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
        limit_per_channel: int,
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
        return messages[:limit_per_channel]

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

    async def _wait_for_qr_login(self, pending: PendingQrLogin) -> None:
        try:
            timeout = max((pending.expires_at - datetime.now(UTC)).total_seconds(), 1)
            await pending.qr_login.wait(timeout=timeout)
            me = await pending.client.get_me()
            pending.user = self._user_to_model(me)
            pending.status = "authorized"
            pending.error = None
        except SessionPasswordNeededError:
            pending.status = "password_required"
            pending.error = None
            return
        except asyncio.TimeoutError:
            pending.status = "expired"
            pending.error = "QR code expired. Generate a new one."
        except asyncio.CancelledError:
            pending.status = "cancelled"
            pending.error = "QR login was cancelled."
            raise
        except Exception as exc:
            pending.status = "error"
            pending.error = str(exc)
        finally:
            if pending.status in {"authorized", "expired", "error", "cancelled"}:
                await self._disconnect_client(pending.client)

    async def _clear_pending_qr(self) -> None:
        pending = self._pending_qr
        if pending is None:
            return

        if pending.wait_task and not pending.wait_task.done():
            pending.wait_task.cancel()
            try:
                await pending.wait_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        await self._disconnect_client(pending.client)
        self._pending_qr = None

    async def _disconnect_client(self, client: TelegramClient) -> None:
        if client.is_connected():
            await client.disconnect()

    def _serialize_qr_state(self, pending: PendingQrLogin) -> dict:
        qr_url = pending.qr_login.url if pending.status == "pending" else None
        qr_image_data_url = self._build_qr_image_data_url(qr_url) if qr_url else None
        return {
            "authorized": pending.status == "authorized",
            "status": pending.status,
            "message": self._qr_status_message(pending.status),
            "user": pending.user.model_dump() if pending.user else None,
            "qr_url": qr_url,
            "qr_image_data_url": qr_image_data_url,
            "expires_at": pending.expires_at.isoformat(),
            "error": pending.error,
            "next_step": self._qr_next_step(pending.status),
        }

    @staticmethod
    def _qr_status_message(status: str) -> str:
        messages = {
            "pending": "Scan the QR code with Telegram on another authorized device.",
            "password_required": "Telegram accepted the QR scan. Enter your 2FA password to finish login.",
            "authorized": "Telegram session authorized via QR login.",
            "expired": "QR code expired. Generate a new one.",
            "error": "QR login failed.",
            "cancelled": "QR login cancelled.",
        }
        return messages.get(status, "QR login is idle.")

    @staticmethod
    def _qr_next_step(status: str) -> str:
        steps = {
            "pending": "Open Telegram on another already authorized device and scan this QR code.",
            "password_required": "Enter your Telegram 2FA password below.",
            "authorized": "You can load messages now.",
            "expired": "Generate a fresh QR code and scan it again.",
            "error": "Start a new QR login attempt.",
            "cancelled": "Generate a fresh QR code to continue.",
        }
        return steps.get(status, "Generate a QR code to start login.")

    @staticmethod
    def _serialize_sent_code(sent_code) -> dict:
        sent_type = getattr(sent_code, "type", None)
        next_type = getattr(sent_code, "next_type", None)
        return {
            "delivery_type": sent_type.__class__.__name__ if sent_type else None,
            "next_delivery_type": next_type.__class__.__name__ if next_type else None,
            "timeout": getattr(sent_code, "timeout", None),
        }

    @staticmethod
    def _build_qr_image_data_url(qr_url: str) -> str:
        buffer = BytesIO()
        image = qrcode.make(qr_url, image_factory=SvgPathImage)
        image.save(buffer)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"

    @staticmethod
    def _user_to_model(user) -> UserInfo:
        return UserInfo(
            id=user.id,
            username=getattr(user, "username", None),
            phone=getattr(user, "phone", None),
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
        )
