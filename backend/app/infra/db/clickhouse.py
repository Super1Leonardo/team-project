from __future__ import annotations

import hashlib
import json
import re
import time
from contextlib import contextmanager
from datetime import UTC, datetime

try:
    import clickhouse_connect
except ModuleNotFoundError:  # pragma: no cover - optional dependency for local/dev setups
    clickhouse_connect = None

from backend.app.common.schemas import (
    MessageSource,
    ParsedMessage,
    ReactionInfo,
    StoredMessagesResponse,
)
from backend.app.core.config import Settings


class ClickHouseMessageStoreError(Exception):
    """Raised when ClickHouse message storage is unavailable or misconfigured."""


class ClickHouseMessageStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._database = self._validate_identifier(settings.clickhouse_database)
        self._table = "raw_mentions"

    def init_db(self, retries: int = 10, delay_seconds: float = 1.0) -> None:
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                with self._client(database="default") as client:
                    client.command(f"CREATE DATABASE IF NOT EXISTS {self._database}")

                with self._client(database=self._database) as client:
                    client.command(
                        f"""
                        CREATE TABLE IF NOT EXISTS {self._table} (
                            message_uid String,
                            project_id String,
                            source_type LowCardinality(String),
                            source_name LowCardinality(String),
                            requested_as String,
                            external_id String,
                            channel_id Int64,
                            channel_title String,
                            channel_username Nullable(String),
                            message_id Int64,
                            message_url Nullable(String),
                            published_at DateTime64(3, 'UTC'),
                            collected_at DateTime64(3, 'UTC'),
                            message_text String,
                            normalized_text String,
                            language Nullable(String),
                            post_author Nullable(String),
                            views Nullable(Int64),
                            forwards Nullable(Int64),
                            like_count Nullable(Int64),
                            dislike_count Nullable(Int64),
                            dedup_key String,
                            reactions_json String,
                            meta_json String
                        )
                        ENGINE = ReplacingMergeTree(collected_at)
                        PARTITION BY toYYYYMM(published_at)
                        ORDER BY (project_id, source_type, published_at, message_uid)
                        """
                    )
                return
            except Exception as exc:
                last_error = exc
                if attempt == retries - 1:
                    break
                time.sleep(delay_seconds)

        raise ClickHouseMessageStoreError("Failed to initialize ClickHouse.") from last_error

    def ping(self) -> None:
        with self._client(database=self._database) as client:
            client.query("SELECT 1")

    def store_messages(self, messages: list[ParsedMessage]) -> int:
        if not messages:
            return 0

        collected_at = datetime.now(UTC)
        rows = [
            [
                self._message_uid(message),
                message.project_id or "default",
                message.source_type,
                message.source_type,
                message.source.requested_as,
                str(message.id),
                message.source.channel_id,
                message.source.title,
                message.source.username,
                message.id,
                message.url,
                message.date,
                collected_at,
                message.text,
                self._normalize_text(message.text),
                None,
                message.post_author,
                message.views,
                message.forwards,
                message.like_count,
                message.dislike_count,
                self._build_dedup_key(message),
                json.dumps(
                    [reaction.model_dump() for reaction in message.reactions],
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "requested_as": message.source.requested_as,
                        "channel_title": message.source.title,
                    },
                    ensure_ascii=False,
                ),
            ]
            for message in messages
        ]

        with self._client(database=self._database) as client:
            client.insert(
                self._table,
                rows,
                column_names=[
                    "message_uid",
                    "project_id",
                    "source_type",
                    "source_name",
                    "requested_as",
                    "external_id",
                    "channel_id",
                    "channel_title",
                    "channel_username",
                    "message_id",
                    "message_url",
                    "published_at",
                    "collected_at",
                    "message_text",
                    "normalized_text",
                    "language",
                    "post_author",
                    "views",
                    "forwards",
                    "like_count",
                    "dislike_count",
                    "dedup_key",
                    "reactions_json",
                    "meta_json",
                ],
            )

        return len(rows)

    def fetch_messages(
        self,
        limit: int = 100,
        source_type: str | None = None,
        channel: str | None = None,
    ) -> StoredMessagesResponse:
        where_parts: list[str] = []

        if source_type:
            where_parts.append(f"source_type = '{self._escape_sql_string(source_type)}'")

        if channel:
            escaped_channel = self._escape_sql_string(channel)
            escaped_username = self._escape_sql_string(channel.removeprefix("@"))
            where_parts.append(
                "("
                f"requested_as = '{escaped_channel}' "
                f"OR channel_username = '{escaped_channel}' "
                f"OR channel_username = '{escaped_username}'"
                ")"
            )

        where_clause = ""
        if where_parts:
            where_clause = "WHERE " + " AND ".join(where_parts)

        sql = f"""
            SELECT
                message_uid,
                project_id,
                source_type,
                requested_as,
                channel_id,
                channel_title,
                channel_username,
                message_id,
                message_text,
                message_url,
                published_at,
                post_author,
                views,
                forwards,
                like_count,
                dislike_count,
                reactions_json
            FROM {self._table} FINAL
            {where_clause}
            ORDER BY published_at DESC, channel_id, message_id DESC
            LIMIT {int(limit)}
        """

        with self._client(database=self._database) as client:
            result = client.query(sql)

        items = [self._row_to_message(row) for row in result.result_rows]
        return StoredMessagesResponse(
            count=len(items),
            storage_backend="clickhouse",
            items=items,
        )

    @contextmanager
    def _client(self, database: str):
        if clickhouse_connect is None:
            raise ClickHouseMessageStoreError(
                "clickhouse_connect is not installed."
            )
        client = clickhouse_connect.get_client(
            host=self.settings.clickhouse_host,
            port=self.settings.clickhouse_port,
            username=self.settings.clickhouse_user,
            password=self.settings.clickhouse_password,
            database=database,
        )
        try:
            yield client
        except Exception as exc:
            raise ClickHouseMessageStoreError(str(exc)) from exc
        finally:
            client.close()

    @staticmethod
    def _row_to_message(row: tuple) -> ParsedMessage:
        (
            message_uid,
            project_id,
            source_type,
            requested_as,
            channel_id,
            channel_title,
            channel_username,
            message_id,
            message_text,
            message_url,
            published_at,
            post_author,
            views,
            forwards,
            like_count,
            dislike_count,
            reactions_json,
        ) = row

        reactions_data = json.loads(reactions_json or "[]")
        reactions = [ReactionInfo.model_validate(item) for item in reactions_data]

        return ParsedMessage(
            message_uid=message_uid,
            project_id=project_id,
            source_type=source_type,
            id=message_id,
            text=message_text,
            date=published_at,
            views=views,
            forwards=forwards,
            post_author=post_author,
            url=message_url,
            like_count=like_count,
            dislike_count=dislike_count,
            reactions=reactions,
            source=MessageSource(
                channel_id=channel_id,
                title=channel_title,
                username=channel_username,
                requested_as=requested_as,
            ),
        )

    @staticmethod
    def _escape_sql_string(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = " ".join(value.casefold().split())
        return normalized

    def _build_dedup_key(self, message: ParsedMessage) -> str:
        base = "|".join(
            [
                message.project_id or "default",
                message.source_type,
                message.source.requested_as,
                self._normalize_text(message.text),
            ]
        )
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _message_uid(self, message: ParsedMessage) -> str:
        if message.message_uid:
            return message.message_uid
        return f"{message.source_type}:{message.source.channel_id}:{message.id}"

    @staticmethod
    def _validate_identifier(value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ClickHouseMessageStoreError(
                "ClickHouse database name must contain only letters, digits, and underscores."
            )
        return value


class ClickHouseMentionEventsStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._database = ClickHouseMessageStore._validate_identifier(
            settings.clickhouse_database
        )
        self._table = "mention_events"

    def init_db(self, retries: int = 10, delay_seconds: float = 1.0) -> None:
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                with self._client(database="default") as client:
                    client.command(f"CREATE DATABASE IF NOT EXISTS {self._database}")

                with self._client(database=self._database) as client:
                    client.command(
                        f"""
                        CREATE TABLE IF NOT EXISTS {self._table} (
                            mention_id UInt64,
                            project_id UInt32,
                            source_type LowCardinality(String),
                            source_id UInt32,
                            author String,
                            relevance_score Float32,
                            relevance_label LowCardinality(String),
                            sentiment_score Float32,
                            sentiment_label LowCardinality(String),
                            has_risk_words UInt8,
                            is_primary UInt8,
                            published_at DateTime,
                            collected_at DateTime,
                            processed_at DateTime,
                            dedup_group_id UInt64
                        )
                        ENGINE = MergeTree()
                        PARTITION BY toYYYYMM(published_at)
                        ORDER BY (project_id, published_at, mention_id)
                        """
                    )
                return
            except Exception as exc:
                last_error = exc
                if attempt == retries - 1:
                    break
                time.sleep(delay_seconds)

        raise ClickHouseMessageStoreError(
            "Failed to initialize mention_events in ClickHouse."
        ) from last_error

    def ping(self) -> None:
        with self._client(database=self._database) as client:
            client.query("SELECT 1")

    def insert_mention_events(self, rows: list[dict]) -> int:
        if not rows:
            return 0

        prepared_rows = [
            [
                row["mention_id"],
                row["project_id"],
                row["source_type"],
                row["source_id"],
                row.get("author", ""),
                row["relevance_score"],
                row["relevance_label"],
                row["sentiment_score"],
                row["sentiment_label"],
                row["has_risk_words"],
                row["is_primary"],
                row["published_at"],
                row["collected_at"],
                row["processed_at"],
                row["dedup_group_id"],
            ]
            for row in rows
        ]

        with self._client(database=self._database) as client:
            client.insert(
                self._table,
                prepared_rows,
                column_names=[
                    "mention_id",
                    "project_id",
                    "source_type",
                    "source_id",
                    "author",
                    "relevance_score",
                    "relevance_label",
                    "sentiment_score",
                    "sentiment_label",
                    "has_risk_words",
                    "is_primary",
                    "published_at",
                    "collected_at",
                    "processed_at",
                    "dedup_group_id",
                ],
            )

        return len(prepared_rows)

    @contextmanager
    def _client(self, database: str):
        if clickhouse_connect is None:
            raise ClickHouseMessageStoreError(
                "clickhouse_connect is not installed."
            )
        client = clickhouse_connect.get_client(
            host=self.settings.clickhouse_host,
            port=self.settings.clickhouse_port,
            username=self.settings.clickhouse_user,
            password=self.settings.clickhouse_password,
            database=database,
        )
        try:
            yield client
        except Exception as exc:
            raise ClickHouseMessageStoreError(str(exc)) from exc
        finally:
            client.close()
