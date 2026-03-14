from __future__ import annotations

from dataclasses import dataclass

from backend.app.infra.db.postgres import BrandRadarPostgresStore


@dataclass(slots=True)
class DedupDecision:
    dedup_group_id: int | None
    is_primary: bool
    matched_mention_id: int | None = None
    distance: float | None = None


class PgVectorDeduplicator:
    def __init__(self, store: BrandRadarPostgresStore, threshold: float = 0.15):
        self.store = store
        self.threshold = threshold

    def assign(self, project_id: int, embedding: list[float]) -> DedupDecision:
        candidates = self.store.find_similar_mentions(project_id, embedding)
        if not candidates:
            return DedupDecision(dedup_group_id=None, is_primary=True)

        best = candidates[0]
        distance = float(best["distance"])
        if distance >= self.threshold:
            return DedupDecision(dedup_group_id=None, is_primary=True)

        group_id = best["dedup_group_id"]
        if group_id is None:
            group_id = self.store.ensure_dedup_group_for_mention(
                project_id,
                int(best["id"]),
            )

        return DedupDecision(
            dedup_group_id=int(group_id),
            is_primary=False,
            matched_mention_id=int(best["id"]),
            distance=distance,
        )
