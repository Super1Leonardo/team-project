from types import SimpleNamespace

from backend.app.modules.sources.service import SourcesService


class _FakeSourcesRepository:
    selected_source = "rss"
    selected_telegram_channels = ["@brand_radar_case"]
    available_telegram_channels = ["@brand_radar_case"]
    selected_rss_feeds = ["https://example.com/feed.xml"]
    available_rss_feeds = ["https://example.com/feed.xml"]

    def get_source_selection(self):
        return {
            "selected_source": "rss",
            "sources": [
                {
                    "id": "telegram",
                    "label": "Telegram",
                    "implemented": True,
                    "description": "Parse messages from selected Telegram channels.",
                },
                {
                    "id": "rss",
                    "label": "RSS",
                    "implemented": True,
                    "description": "Parse publications from configured RSS/Atom feed URLs.",
                },
            ],
            "message": "RSS source selected.",
        }


def test_app_config_exposes_rss_selection_and_feeds() -> None:
    service = SourcesService(
        repository=_FakeSourcesRepository(),
        settings=SimpleNamespace(
            api_title="Telegram Parser API",
            api_version="0.1.0",
        ),
    )

    payload = service.get_app_config()

    assert payload.selected_source == "rss"
    assert payload.selected_rss_feeds == ["https://example.com/feed.xml"]
    assert payload.available_rss_feeds == ["https://example.com/feed.xml"]
    assert any(source.id == "rss" for source in payload.available_sources)

