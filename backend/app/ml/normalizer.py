from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from backend.app.core.exceptions import ExternalMLResponseError

if TYPE_CHECKING:
    from backend.app.infra.db.postgres import BrandRadarPostgresStore


class MLResultNormalizer:
    def __init__(
        self,
        store: BrandRadarPostgresStore,
        *,
        dedup_threshold: float = 0.15,
    ):
        self.store = store
        self.dedup_threshold = dedup_threshold

    @staticmethod
    def build_queue_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "raw_post_id": int(row["id"]),
                "source_id": int(row["source_id"]),
                "project_id": int(row["project_id"]),
                "source_type": row["source_type"],
                "external_id": row["external_id"],
                "url": row["url"],
                "title": row["title"],
                "text": row["text"],
                "author": row["author"],
                "published_at": row["published_at"],
                "collected_at": row["collected_at"],
                "raw_meta": row["raw_meta"],
                "keywords": row["keywords"],
                "exclude_keywords": row["exclude_keywords"],
                "risk_words": row["risk_words"],
            }
            for row in rows
        ]

    @staticmethod
    def extract_remote_results(remote_response: Any) -> list[dict[str, Any]]:
        if isinstance(remote_response, list):
            results = remote_response
        elif isinstance(remote_response, dict):
            for key in ("results", "items", "predictions", "data"):
                value = remote_response.get(key)
                if isinstance(value, list):
                    results = value
                    break
            else:
                raise ExternalMLResponseError(
                    "External ML response must contain a list in one of: results, items, predictions, data."
                )
        else:
            raise ExternalMLResponseError("External ML response has unsupported format.")

        if not all(isinstance(item, dict) for item in results):
            raise ExternalMLResponseError("External ML response items must be JSON objects.")
        return results

    def normalize_remote_results(
        self,
        *,
        queue_items: list[dict[str, Any]],
        remote_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        queue_by_raw_post_id = {
            int(item["raw_post_id"]): item
            for item in queue_items
        }
        normalized_rows: list[dict[str, Any]] = []

        for index, result in enumerate(remote_results):
            queue_item = self._resolve_queue_item(
                queue_items=queue_items,
                queue_by_raw_post_id=queue_by_raw_post_id,
                remote_item=result,
                index=index,
            )
            relevance_label = self._normalize_relevance_label(result)
            relevance_score = self._normalize_float(
                result,
                keys=("relevance_score", "score", "relevance_probability"),
                default=1.0 if relevance_label == "relevant" else 0.0,
            )
            sentiment_label = self._normalize_sentiment_label(result)
            sentiment_score = self._normalize_float(
                result,
                keys=("sentiment_score", "sentiment_value", "polarity"),
                default=0.0,
            )
            has_risk_words = bool(
                result.get(
                    "has_risk_words",
                    self._contains_any(queue_item["text"], queue_item["risk_words"]),
                )
            )
            embedding = self._normalize_embedding(result.get("embedding"))
            dedup_group_id, is_primary = self._assign_dedup(
                project_id=int(queue_item["project_id"]),
                relevance_label=relevance_label,
                embedding=embedding,
            )

            normalized_rows.append(
                {
                    "raw_post_id": int(queue_item["raw_post_id"]),
                    "project_id": int(queue_item["project_id"]),
                    "relevance_score": relevance_score,
                    "relevance_label": relevance_label,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "has_risk_words": has_risk_words,
                    "embedding": embedding,
                    "dedup_group_id": dedup_group_id,
                    "is_primary": is_primary,
                    "processed_at": self._parse_datetime(result.get("processed_at")),
                }
            )

        return normalized_rows

    @staticmethod
    def _resolve_queue_item(
        *,
        queue_items: list[dict[str, Any]],
        queue_by_raw_post_id: dict[int, dict[str, Any]],
        remote_item: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        raw_post_id = remote_item.get("raw_post_id")
        if raw_post_id is not None:
            matched = queue_by_raw_post_id.get(int(raw_post_id))
            if matched is None:
                raise ExternalMLResponseError(
                    f"External ML returned unknown raw_post_id={raw_post_id}."
                )
            return matched

        if index >= len(queue_items):
            raise ExternalMLResponseError(
                "External ML returned more results than queued items and some results have no raw_post_id."
            )
        return queue_items[index]

    def _assign_dedup(
        self,
        *,
        project_id: int,
        relevance_label: str,
        embedding: list[float],
    ) -> tuple[int | None, bool]:
        if relevance_label != "relevant":
            return None, True

        candidates = self.store.find_similar_mentions(project_id, embedding)
        if not candidates:
            return None, True

        best = candidates[0]
        distance = float(best["distance"])
        if distance >= self.dedup_threshold:
            return None, True

        group_id = best["dedup_group_id"]
        if group_id is None:
            group_id = self.store.ensure_dedup_group_for_mention(
                project_id,
                int(best["id"]),
            )

        return int(group_id), False

    @staticmethod
    def _normalize_float(
        payload: dict[str, Any],
        *,
        keys: tuple[str, ...],
        default: float,
    ) -> float:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return float(default)

    @staticmethod
    def _normalize_relevance_label(payload: dict[str, Any]) -> str:
        raw_value = payload.get("relevance_label", payload.get("relevance"))
        if isinstance(raw_value, bool):
            return "relevant" if raw_value else "irrelevant"
        if isinstance(raw_value, str):
            normalized = raw_value.strip().casefold()
            if normalized in {"relevant", "relevance", "true", "1", "yes"}:
                return "relevant"
            if normalized in {"irrelevant", "false", "0", "no"}:
                return "irrelevant"

        if "is_relevant" in payload:
            return "relevant" if bool(payload["is_relevant"]) else "irrelevant"

        raise ExternalMLResponseError(
            "External ML result is missing a valid relevance label."
        )

    @staticmethod
    def _normalize_sentiment_label(payload: dict[str, Any]) -> str:
        raw_value = payload.get("sentiment_label", payload.get("sentiment"))
        if isinstance(raw_value, str):
            normalized = raw_value.strip().casefold()
            if normalized in {"positive", "neutral", "negative"}:
                return normalized
        return "neutral"

    @staticmethod
    def _normalize_embedding(embedding: Any) -> list[float]:
        if isinstance(embedding, list) and len(embedding) == 384:
            try:
                return [float(value) for value in embedding]
            except (TypeError, ValueError):
                pass
        raise ExternalMLResponseError(
            "External ML result must contain a valid embedding with 384 numeric values."
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @staticmethod
    def _contains_any(text: str, words: list[str]) -> bool:
        normalized = " ".join(text.casefold().split())
        return any(" ".join(word.casefold().split()) in normalized for word in words)
