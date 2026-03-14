from __future__ import annotations

import time

import psycopg

from backend.app.common.schemas import ParserSource
from backend.app.core.config import Settings
from backend.app.modules.sources.constants import (
    AVAILABLE_TELEGRAM_CHANNELS,
    DEFAULT_TELEGRAM_CHANNELS,
)

SOURCE_OPTIONS = (
    {
        "id": "telegram",
        "label": "Telegram",
        "implemented": True,
        "description": "Parse messages from selected Telegram channels.",
    },
    {
        "id": "website",
        "label": "Website",
        "implemented": False,
        "description": "Placeholder source. Website parsing is not implemented yet.",
    },
)


class ParserSettingsRepository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._available_telegram_channels = list(AVAILABLE_TELEGRAM_CHANNELS)

    def init_db(self, retries: int = 10, delay_seconds: float = 1.0) -> None:
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                with self._connect() as conn, conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS parser_settings (
                            id SMALLINT PRIMARY KEY CHECK (id = 1),
                            selected_source TEXT NOT NULL
                                CHECK (selected_source IN ('telegram', 'website'))
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS parser_selected_channels (
                            channel TEXT PRIMARY KEY,
                            position INTEGER NOT NULL
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS text_analysis_results (
                            id BIGSERIAL PRIMARY KEY,
                            text_source TEXT NOT NULL,
                            text_reference TEXT NOT NULL,
                            relevance DOUBLE PRECISION,
                            aggression DOUBLE PRECISION,
                            womp DOUBLE PRECISION,
                            sentiment TEXT,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            UNIQUE (text_source, text_reference)
                        )
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE parser_selected_channels
                        ADD COLUMN IF NOT EXISTS position INTEGER NOT NULL DEFAULT 0
                        """
                    )
                    cur.execute(
                        """
                        INSERT INTO parser_settings (id, selected_source)
                        VALUES (1, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        ("telegram",),
                    )
                    cur.execute("SELECT COUNT(*) FROM parser_selected_channels")
                    count = cur.fetchone()[0]
                    if count == 0:
                        cur.executemany(
                            """
                            INSERT INTO parser_selected_channels (channel, position)
                            VALUES (%s, %s)
                            ON CONFLICT (channel) DO UPDATE
                            SET position = EXCLUDED.position
                            """,
                            [
                                (channel, index)
                                for index, channel in enumerate(DEFAULT_TELEGRAM_CHANNELS)
                            ],
                        )
                return
            except psycopg.OperationalError as exc:
                last_error = exc
                if attempt == retries - 1:
                    break
                time.sleep(delay_seconds)

        if last_error is not None:
            raise last_error

    @property
    def selected_source(self) -> ParserSource:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT selected_source FROM parser_settings WHERE id = 1")
            row = cur.fetchone()
        if not row:
            return "telegram"
        return row[0]

    @property
    def selected_telegram_channels(self) -> list[str]:
        channels = self._read_selected_channels()
        if channels:
            return channels
        self._seed_default_channels()
        return self._read_selected_channels()

    @property
    def available_telegram_channels(self) -> list[str]:
        return list(self._available_telegram_channels)

    def get_source_selection(self, message: str | None = None) -> dict:
        selected_source = self.selected_source
        return {
            "selected_source": selected_source,
            "sources": list(SOURCE_OPTIONS),
            "message": message or self._source_message(selected_source),
        }

    def set_source(self, source: ParserSource) -> dict:
        if source not in {"telegram", "website"}:
            raise ValueError("Unsupported source. Use 'telegram' or 'website'.")

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO parser_settings (id, selected_source)
                VALUES (1, %s)
                ON CONFLICT (id)
                DO UPDATE SET selected_source = EXCLUDED.selected_source
                """,
                (source,),
            )

        return self.get_source_selection()

    def get_telegram_channels(self, message: str | None = None) -> dict:
        return {
            "selected_source": self.selected_source,
            "available_channels": self.available_telegram_channels,
            "selected_channels": self.selected_telegram_channels,
            "message": message or "Telegram channels ready for parsing.",
        }

    def set_telegram_channels(self, channels: list[str]) -> dict:
        cleaned_channels: list[str] = []
        seen: set[str] = set()

        for channel in channels:
            normalized = channel.strip()
            if not normalized or normalized in seen:
                continue
            cleaned_channels.append(normalized)
            seen.add(normalized)

        if not cleaned_channels:
            raise ValueError("Choose at least one Telegram channel.")

        invalid_channels = [
            channel
            for channel in cleaned_channels
            if channel not in self._available_telegram_channels
        ]
        if invalid_channels:
            raise ValueError(
                "Unknown Telegram channels: " + ", ".join(invalid_channels) + "."
            )

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM parser_selected_channels")
            cur.executemany(
                """
                INSERT INTO parser_selected_channels (channel, position)
                VALUES (%s, %s)
                """,
                [(channel, index) for index, channel in enumerate(cleaned_channels)],
            )

        return self.get_telegram_channels(message="Telegram channels updated.")

    def _read_selected_channels(self) -> list[str]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT channel
                FROM parser_selected_channels
                ORDER BY position, channel
                """
            )
            rows = cur.fetchall()

        channels = [row[0] for row in rows if row[0] in self._available_telegram_channels]
        return channels

    def _seed_default_channels(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO parser_selected_channels (channel, position)
                VALUES (%s, %s)
                ON CONFLICT (channel) DO UPDATE
                SET position = EXCLUDED.position
                """,
                [(channel, index) for index, channel in enumerate(DEFAULT_TELEGRAM_CHANNELS)],
            )

    def _connect(self):
        return psycopg.connect(self.settings.parser_database_url, autocommit=True)

    @staticmethod
    def _source_message(source: ParserSource) -> str:
        if source == "telegram":
            return "Telegram source selected."
        return "Website source selected. Parsing is a placeholder for now."
