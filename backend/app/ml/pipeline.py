from __future__ import annotations

from backend.app.infra.db.clickhouse import ClickHouseMentionEventsStore
from backend.app.infra.db.postgres import BrandRadarPostgresStore
from backend.app.ml.dedup import PgVectorDeduplicator
from backend.app.ml.embeddings import HashEmbeddingEncoder
from backend.app.ml.relevance import KeywordRelevanceClassifier
from backend.app.ml.sentiment import LexiconSentimentAnalyzer


class MLPipeline:
    def __init__(
        self,
        store: BrandRadarPostgresStore,
        clickhouse_store: ClickHouseMentionEventsStore,
        relevance: KeywordRelevanceClassifier | None = None,
        sentiment: LexiconSentimentAnalyzer | None = None,
        embeddings: HashEmbeddingEncoder | None = None,
        deduplicator: PgVectorDeduplicator | None = None,
    ):
        self.store = store
        self.clickhouse_store = clickhouse_store
        self.relevance = relevance or KeywordRelevanceClassifier()
        self.sentiment = sentiment or LexiconSentimentAnalyzer()
        self.embeddings = embeddings or HashEmbeddingEncoder()
        self.deduplicator = deduplicator or PgVectorDeduplicator(store)

    def process_batch(self, limit: int = 100) -> dict:
        raw_posts = self.store.fetch_unprocessed_raw_posts(limit=limit)
        if not raw_posts:
            return {
                "batch_size": 0,
                "stored_count": 0,
                "synced_count": 0,
                "projects": {},
            }

        mention_rows: list[dict] = []

        for raw_post in raw_posts:
            relevance_label, relevance_score = self.relevance.classify(
                raw_post["text"],
                raw_post["keywords"],
                raw_post["exclude_keywords"],
            )
            if relevance_label == "relevant":
                sentiment_label, sentiment_score = self.sentiment.analyze(raw_post["text"])
            else:
                sentiment_label, sentiment_score = "neutral", 0.0

            embedding = self.embeddings.encode(raw_post["text"])
            has_risk_words = self._contains_any(raw_post["text"], raw_post["risk_words"])
            dedup = (
                self.deduplicator.assign(int(raw_post["project_id"]), embedding)
                if relevance_label == "relevant"
                else None
            )

            mention_rows.append(
                {
                    "raw_post_id": int(raw_post["id"]),
                    "project_id": int(raw_post["project_id"]),
                    "relevance_score": relevance_score,
                    "relevance_label": relevance_label,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "has_risk_words": has_risk_words,
                    "embedding": embedding,
                    "dedup_group_id": dedup.dedup_group_id if dedup else None,
                    "is_primary": dedup.is_primary if dedup else True,
                }
            )

        result = self.store.persist_mentions(
            mention_rows,
            sync_callback=self.clickhouse_store.insert_mention_events,
        )
        return {
            "batch_size": len(raw_posts),
            "stored_count": result["stored_count"],
            "synced_count": result["synced_count"],
            "projects": result["projects"],
        }

    @staticmethod
    def _contains_any(text: str, words: list[str]) -> bool:
        normalized = " ".join(text.casefold().split())
        return any(" ".join(word.casefold().split()) in normalized for word in words)
