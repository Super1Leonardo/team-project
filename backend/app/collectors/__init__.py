from __future__ import annotations

__all__ = ["BaseCollector", "TelegramCollector", "RssCollector", "WebsiteCollector"]


def __getattr__(name: str):
    if name == "BaseCollector":
        from backend.app.collectors.base import BaseCollector

        return BaseCollector
    if name == "TelegramCollector":
        from backend.app.collectors.telegram import TelegramCollector

        return TelegramCollector
    if name == "RssCollector":
        from backend.app.collectors.rss import RssCollector

        return RssCollector
    if name == "WebsiteCollector":
        from backend.app.collectors.website import WebsiteCollector

        return WebsiteCollector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
