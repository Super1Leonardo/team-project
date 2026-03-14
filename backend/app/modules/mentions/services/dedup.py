from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.common.types import combine_title_text, normalize_text, normalize_url, sha256_hex
from app.modules.mentions.repository import MentionRepository


@dataclass(slots=True)
class DedupResult:
    url_hash: str | None
    content_hash: str
    is_duplicate: bool
    duplicate_of_id: uuid.UUID | None = None
    cluster_id: str | None = None
    duplicate_reason: str | None = None


class DeduplicationService:
    def __init__(self, mention_repository: MentionRepository) -> None:
        self.mention_repository = mention_repository

    async def detect(
        self,
        project_id: uuid.UUID,
        source_id: uuid.UUID,
        *,
        title: str,
        text: str,
        raw_url: str | None,
    ) -> DedupResult:
        normalized_url = normalize_url(raw_url)
        url_hash = sha256_hex(normalized_url) if normalized_url else None
        normalized_content = normalize_text(combine_title_text(title, text))
        content_hash = sha256_hex(normalized_content)

        existing = await self.mention_repository.find_by_url_hash(project_id, source_id, url_hash)
        if existing is not None:
            return DedupResult(
                url_hash=url_hash,
                content_hash=content_hash,
                is_duplicate=True,
                duplicate_of_id=existing.id,
                cluster_id=existing.cluster_id or str(existing.id),
                duplicate_reason="url_hash",
            )

        existing = await self.mention_repository.find_by_content_hash(project_id, source_id, content_hash)
        if existing is not None:
            return DedupResult(
                url_hash=url_hash,
                content_hash=content_hash,
                is_duplicate=True,
                duplicate_of_id=existing.id,
                cluster_id=existing.cluster_id or str(existing.id),
                duplicate_reason="content_hash",
            )

        return DedupResult(url_hash=url_hash, content_hash=content_hash, is_duplicate=False)
