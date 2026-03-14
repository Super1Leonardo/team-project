from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None

    parsed = value
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def floor_to_window(value: datetime, minutes: int) -> datetime:
    safe_minutes = max(minutes, 1)
    normalized = ensure_utc(value)
    minute_slot = (normalized.minute // safe_minutes) * safe_minutes
    return normalized.replace(minute=minute_slot, second=0, microsecond=0)


def minus_minutes(value: datetime, minutes: int) -> datetime:
    return ensure_utc(value) - timedelta(minutes=minutes)


def isoformat_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_utc(value).isoformat().replace("+00:00", "Z")
