from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO

import qrcode
from qrcode.image.svg import SvgPathImage
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.tl.types import ReactionCustomEmoji, ReactionEmoji

from backend.channels import TARGET_CHANNELS
from backend.config import Settings
from backend.models import (
    AuthStatusResponse,
    ChannelParseResult,
    MessageSource,
    ParseResponse,
    ParsedMessage,
    ReactionInfo,
    UserInfo,
)


class TelegramServiceError(Exception):
    """Base service error."""


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


class TelegramService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._pending_codes: dict[str, PendingCode] = {}
        self._pending_qr: PendingQrLogin | None = None
        self._qr_lock = asyncio.Lock()

    def _ensure_credentials(self) -> None:
        if not self.settings.credentials_configured:
            raise TelegramConfigurationError(
                "Set TELEGRAM_API_ID and TELEGRAM_API_HASH before using the parser."
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

    async def get_auth_status(self) -> AuthStatusResponse:
        if not self.settings.credentials_configured:
            return AuthStatusResponse(
                configured=False,
                authorized=False,
                phone_hint=self.settings.telegram_phone,
                user=None,
                selected_channels=TARGET_CHANNELS,
            )

        pending = self._pending_qr
        if pending and pending.status in {"pending", "password_required"}:
            return AuthStatusResponse(
                configured=True,
                authorized=False,
                phone_hint=self.settings.telegram_phone,
                user=None,
                selected_channels=TARGET_CHANNELS,
            )

        if pending and pending.status == "authorized" and pending.user:
            return AuthStatusResponse(
                configured=True,
                authorized=True,
                phone_hint=self.settings.telegram_phone,
                user=pending.user,
                selected_channels=TARGET_CHANNELS,
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
                selected_channels=TARGET_CHANNELS,
            )

    async def start_qr_login(self, recreate: bool = False) -> dict:
        async with self._qr_lock:
            pending = self._pending_qr
            if pending and pending.status in {"pending", "password_required"} and not recreate:
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
                        "user": auth_status.user.model_dump() if auth_status.user else None,
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
                raise TelegramServiceError("QR login is not waiting for a 2FA password.")

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
                    "requested_at": self._pending_codes[phone_value].requested_at.isoformat(),
                    **delivery,
                }
        except PhoneNumberInvalidError as exc:
            raise TelegramServiceError("Invalid phone number format for Telegram.") from exc
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

    async def logout(self) -> dict:
        await self._clear_pending_qr()
        async with self._client() as client:
            authorized = await client.is_user_authorized()
            if not authorized:
                return {"authorized": False, "message": "Session is already logged out."}

            await client.log_out()
            return {"authorized": False, "message": "Telegram session logged out."}

    async def parse_configured_channels(
        self,
        limit_per_channel: int = 20,
        channels: list[str] | None = None,
    ) -> ParseResponse:
        requested_channels = channels or TARGET_CHANNELS
        async with self._client() as client:
            if not await client.is_user_authorized():
                raise TelegramUnauthorizedError(
                    "Telegram session is not authorized. Complete auth first."
                )

            all_items: list[ParsedMessage] = []
            results: list[ChannelParseResult] = []

            for channel_ref in requested_channels:
                try:
                    entity = await client.get_entity(channel_ref)
                    messages = [
                        self._serialize_message(message, entity, channel_ref)
                        async for message in client.iter_messages(
                            entity,
                            limit=limit_per_channel,
                        )
                    ]
                    results.append(
                        ChannelParseResult(
                            requested_as=channel_ref,
                            title=getattr(entity, "title", channel_ref),
                            username=getattr(entity, "username", None),
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

            return ParseResponse(
                authorized=True,
                count=len(all_items),
                channels=requested_channels,
                items=all_items,
                results=results,
            )

    def _serialize_message(self, message, entity, requested_as: str) -> ParsedMessage:
        reactions = self._extract_reactions(message)
        reaction_map = {item.key: item.count for item in reactions}
        username = getattr(entity, "username", None)
        message_url = f"https://t.me/{username}/{message.id}" if username else None

        return ParsedMessage(
            id=message.id,
            text=message.message or "",
            date=message.date,
            views=getattr(message, "views", None),
            forwards=getattr(message, "forwards", None),
            post_author=getattr(message, "post_author", None),
            url=message_url,
            like_count=reaction_map.get("\U0001F44D"),
            dislike_count=reaction_map.get("\U0001F44E"),
            reactions=reactions,
            source=MessageSource(
                channel_id=entity.id,
                title=getattr(entity, "title", requested_as),
                username=username,
                requested_as=requested_as,
            ),
        )

    def _extract_reactions(self, message) -> list[ReactionInfo]:
        if not getattr(message, "reactions", None):
            return []

        items: list[ReactionInfo] = []
        for result in getattr(message.reactions, "results", []) or []:
            reaction_obj = getattr(result, "reaction", None)
            if isinstance(reaction_obj, ReactionEmoji):
                key = reaction_obj.emoticon
                reaction_type = "emoji"
            elif isinstance(reaction_obj, ReactionCustomEmoji):
                key = str(reaction_obj.document_id)
                reaction_type = "custom_emoji"
            else:
                key = reaction_obj.__class__.__name__ if reaction_obj else "unknown"
                reaction_type = "unknown"

            items.append(
                ReactionInfo(
                    key=key,
                    count=result.count,
                    type=reaction_type,
                )
            )
        return items

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
        return {
            "authorized": pending.status == "authorized",
            "status": pending.status,
            "message": self._qr_status_message(pending.status),
            "user": pending.user.model_dump() if pending.user else None,
            "qr_url": qr_url,
            "qr_image_data_url": self._build_qr_image_data_url(qr_url) if qr_url else None,
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
    def _build_qr_image_data_url(url: str) -> str:
        buffer = BytesIO()
        image = qrcode.make(url, image_factory=SvgPathImage, box_size=10, border=2)
        image.save(buffer)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"

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
    def _user_to_model(user) -> UserInfo:
        return UserInfo(
            id=user.id,
            username=getattr(user, "username", None),
            phone=getattr(user, "phone", None),
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
        )
