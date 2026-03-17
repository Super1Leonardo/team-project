from __future__ import annotations

import re
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from backend.app.core.exceptions import ExternalMLResponseError

ML_CONFIDENCE_KEYS = (
    "relevance_score",
    "confidence",
    "confidence_score",
    "score",
    "relevance_probability",
    "confidence_probability",
)

if TYPE_CHECKING:
    from backend.app.infra.db.postgres import BrandRadarPostgresStore


class MLResultNormalizer:
    def __init__(
        self,
        store: BrandRadarPostgresStore,
        *,
        dedup_threshold: float = 0.15,
        cluster_threshold: float | None = None,
    ):
        self.store = store
        self.dedup_threshold = dedup_threshold
        self.cluster_threshold = cluster_threshold or dedup_threshold

    @staticmethod
    def build_queue_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "raw_post_id": int(row["id"]),
                "source_id": int(row["source_id"]),
                "project_id": int(row["project_id"]),
                "source_type": row["source_type"],
                "company": row.get("company", row.get("project_name", "")),
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
        self._validate_result_mapping(
            queue_items=queue_items,
            remote_results=remote_results,
        )
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
            searchable_text = self._build_searchable_text(queue_item)
            sentiment_label = self._normalize_sentiment_label(result)
            has_keyword_match = self._matches_keywords(
                searchable_text,
                queue_item["keywords"],
            )
            has_excluded_match = self._contains_any(
                searchable_text,
                queue_item["exclude_keywords"],
            )
            relevance_label = self._normalize_relevance_label(result)
            relevance_score = 0.0
            if has_excluded_match or not has_keyword_match:
                relevance_label = "irrelevant"
            else:
                relevance_score = self._normalize_required_relevance_score(
                    result,
                    sentiment_label=sentiment_label,
                )
            sentiment_score = self._normalize_float(
                result,
                keys=("sentiment_score", "sentiment_value", "polarity"),
                default=0.0,
            )
            has_risk_words = self._contains_any(
                searchable_text,
                queue_item["risk_words"],
            )
            embedding = self._normalize_embedding(
                self._extract_embedding_payload(result)
            )
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

    def split_queue_items_for_ml(
        self,
        queue_items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        ml_queue_items: list[dict[str, Any]] = []
        skipped_queue_items: list[dict[str, Any]] = []

        for item in queue_items:
            if self._should_send_to_ml(item):
                ml_queue_items.append(item)
            else:
                skipped_queue_items.append(item)

        return ml_queue_items, skipped_queue_items

    def build_local_irrelevant_rows(
        self,
        queue_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "raw_post_id": int(item["raw_post_id"]),
                "project_id": int(item["project_id"]),
                "relevance_score": 0.0,
                "relevance_label": "irrelevant",
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "has_risk_words": self._contains_any(
                    self._build_searchable_text(item),
                    item["risk_words"],
                ),
                "embedding": None,
                "dedup_group_id": None,
                "is_primary": True,
                "processed_at": None,
            }
            for item in queue_items
        ]

    @staticmethod
    def _validate_result_mapping(
        *,
        queue_items: list[dict[str, Any]],
        remote_results: list[dict[str, Any]],
    ) -> None:
        if not remote_results:
            if queue_items:
                raise ExternalMLResponseError(
                    "External ML returned no results for queued items without raw_post_id mapping."
                )
            return

        if all(result.get("raw_post_id") is not None for result in remote_results):
            return

        if len(remote_results) != len(queue_items):
            raise ExternalMLResponseError(
                "External ML returned a different number of results than queued items without raw_post_id mapping."
            )

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
        embedding: list[float] | None,
    ) -> tuple[int | None, bool]:
        if relevance_label != "relevant" or embedding is None:
            return None, True

        cluster_candidates = self.store.find_similar_clusters(project_id, embedding)
        if cluster_candidates:
            best_cluster = cluster_candidates[0]
            cluster_distance = float(best_cluster["distance"])
            if cluster_distance < self.cluster_threshold:
                return int(best_cluster["id"]), False

        mention_candidates = self.store.find_similar_mentions(project_id, embedding)
        if not mention_candidates:
            return None, True

        best_mention = mention_candidates[0]
        mention_distance = float(best_mention["distance"])
        if mention_distance >= self.cluster_threshold:
            return None, True

        group_id = best_mention["dedup_group_id"]
        if group_id is None:
            group_id = self.store.ensure_dedup_group_for_mention(
                project_id,
                int(best_mention["id"]),
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

    @classmethod
    def _normalize_required_relevance_score(
        cls,
        payload: dict[str, Any],
        *,
        sentiment_label: str,
    ) -> float:
        for key in ML_CONFIDENCE_KEYS:
            score = cls._coerce_confidence_value(
                payload.get(key),
                sentiment_label=sentiment_label,
            )
            if score is not None:
                return score
        raise ExternalMLResponseError(
            "External ML result must contain a valid relevance score in one of: "
            + ", ".join(ML_CONFIDENCE_KEYS)
            + "."
        )

    @staticmethod
    def _coerce_confidence_value(
        value: Any,
        *,
        sentiment_label: str,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, dict):
            normalized_map = {
                str(key).strip().casefold(): item_value
                for key, item_value in value.items()
            }
            sentiment_value = normalized_map.get(sentiment_label)
            if sentiment_value is None:
                return None
            try:
                return float(sentiment_value)
            except (TypeError, ValueError):
                return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

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

        return "relevant"

    @staticmethod
    def _normalize_sentiment_label(payload: dict[str, Any]) -> str:
        raw_value = payload.get("sentiment_label", payload.get("sentiment"))
        if isinstance(raw_value, str):
            normalized = raw_value.strip().casefold()
            if normalized in {"positive", "neutral", "negative"}:
                return normalized
        return "neutral"

    @staticmethod
    def _normalize_embedding(embedding: Any) -> list[float] | None:
        if embedding is None:
            return None
        if isinstance(embedding, list) and len(embedding) == 384:
            try:
                return [float(value) for value in embedding]
            except (TypeError, ValueError):
                pass
        raise ExternalMLResponseError(
            "External ML result must contain a valid embedding with 384 numeric values."
        )

    @staticmethod
    def _extract_embedding_payload(payload: dict[str, Any]) -> Any:
        embedding = payload.get("embedding")
        if embedding is not None:
            return embedding

        cluster = payload.get("cluster")
        if isinstance(cluster, dict):
            return cluster.get("embedding")

        return None

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
        normalized_text = MLResultNormalizer._normalize_text(text)
        for word in words:
            pattern = MLResultNormalizer._compile_keyword_pattern(word)
            if pattern is not None and pattern.search(normalized_text):
                return True
        return False

    @classmethod
    def _matches_keywords(cls, text: str, keywords: list[str]) -> bool:
        if not keywords:
            return True
        return cls._contains_any(text, keywords)

    @classmethod
    def _should_send_to_ml(cls, queue_item: dict[str, Any]) -> bool:
        searchable_text = cls._build_searchable_text(queue_item)
        has_keyword_match = cls._matches_keywords(
            searchable_text,
            queue_item["keywords"],
        )
        has_excluded_match = cls._contains_any(
            searchable_text,
            queue_item["exclude_keywords"],
        )
        return has_keyword_match and not has_excluded_match

    @staticmethod
    def _build_searchable_text(queue_item: dict[str, Any]) -> str:
        title = str(queue_item.get("title") or "").strip()
        text = str(queue_item.get("text") or "").strip()
        if title and text:
            return f"{title}\n{text}"
        return title or text

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _is_word_char(value: str) -> bool:
        return value.isalnum() or value == "_"

    @staticmethod
    @lru_cache(maxsize=1024)
    def _compile_keyword_pattern(word: str) -> re.Pattern[str] | None:
        normalized_word = MLResultNormalizer._normalize_text(word)
        if not normalized_word:
            return None

        escaped = re.escape(normalized_word).replace(r"\ ", r"\s+")
        prefix = r"(?<!\w)" if MLResultNormalizer._is_word_char(normalized_word[0]) else ""
        suffix = r"(?!\w)" if MLResultNormalizer._is_word_char(normalized_word[-1]) else ""
        return re.compile(prefix + escaped + suffix)
