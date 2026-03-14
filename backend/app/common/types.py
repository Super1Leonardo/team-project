from __future__ import annotations

import hashlib
import re
from typing import Any, TypeAlias
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = Any

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.casefold()
    cleaned = _PUNCTUATION_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def tokenize(value: str | None) -> list[str]:
    return [token for token in normalize_text(value).split(" ") if token]


def combine_title_text(title: str | None, text: str | None) -> str:
    return " ".join(part.strip() for part in [title or "", text or ""] if part and part.strip()).strip()


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None

    parsed = urlsplit(raw_url.strip())
    if not parsed.scheme or not parsed.netloc:
        return raw_url.strip()

    normalized_query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    normalized_path = parsed.path.rstrip("/") or "/"

    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            normalized_query,
            "",
        )
    )
