from __future__ import annotations

import uuid

from app.core.constants import EVENT_BRAND_CREATED, EVENT_BRAND_UPDATED
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.time import utc_now
from app.modules.brands.models import Brand
from app.modules.brands.repository import BrandRepository
from app.modules.brands.schemas import BrandCreate, BrandUpdate
from app.modules.events.service import EventLogService
from app.modules.projects.repository import ProjectRepository


def _normalize_terms(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


class BrandService:
    def __init__(
        self,
        repository: BrandRepository,
        project_repository: ProjectRepository,
        event_log_service: EventLogService,
    ) -> None:
        self.repository = repository
        self.project_repository = project_repository
        self.event_log_service = event_log_service

    async def list(self, project_id: uuid.UUID | None = None) -> list[Brand]:
        return await self.repository.list(project_id=project_id)

    async def create(self, data: BrandCreate) -> Brand:
        project = await self.project_repository.get(data.project_id)
        if project is None:
            raise NotFoundError(f"Project '{data.project_id}' not found")

        name = data.name.strip()
        if not _normalize_terms(data.keywords):
            raise ValidationError("Brand must contain at least one keyword")

        existing = await self.repository.get_by_name(data.project_id, name)
        if existing is not None:
            raise ConflictError(f"Brand with name '{name}' already exists in this project")

        now = utc_now()
        brand = Brand(
            id=uuid.uuid4(),
            project_id=data.project_id,
            name=name,
            keywords=_normalize_terms(data.keywords),
            exceptions=_normalize_terms(data.exceptions),
            risk_words=_normalize_terms(data.risk_words),
            spike_threshold=data.spike_threshold,
            spike_window_minutes=data.spike_window_minutes,
            spike_cooldown_minutes=data.spike_cooldown_minutes,
            created_at=now,
            updated_at=now,
        )
        saved = await self.repository.add(brand)
        await self.event_log_service.record(
            EVENT_BRAND_CREATED,
            "brand",
            entity_id=saved.id,
            payload={"project_id": str(saved.project_id), "name": saved.name},
        )
        return saved

    async def update(self, brand_id: uuid.UUID, data: BrandUpdate) -> Brand:
        brand = await self.repository.get(brand_id)
        if brand is None:
            raise NotFoundError(f"Brand '{brand_id}' not found")

        if data.name is not None:
            name = data.name.strip()
            existing = await self.repository.get_by_name(brand.project_id, name)
            if existing is not None and existing.id != brand.id:
                raise ConflictError(f"Brand with name '{name}' already exists in this project")
            brand.name = name

        if data.keywords is not None:
            normalized_keywords = _normalize_terms(data.keywords)
            if not normalized_keywords:
                raise ValidationError("Brand must contain at least one keyword")
            brand.keywords = normalized_keywords
        if data.exceptions is not None:
            brand.exceptions = _normalize_terms(data.exceptions)
        if data.risk_words is not None:
            brand.risk_words = _normalize_terms(data.risk_words)
        if data.spike_threshold is not None:
            brand.spike_threshold = data.spike_threshold
        if data.spike_window_minutes is not None:
            brand.spike_window_minutes = data.spike_window_minutes
        if data.spike_cooldown_minutes is not None:
            brand.spike_cooldown_minutes = data.spike_cooldown_minutes

        brand.updated_at = utc_now()
        saved = await self.repository.update(brand)
        await self.event_log_service.record(
            EVENT_BRAND_UPDATED,
            "brand",
            entity_id=saved.id,
            payload={"project_id": str(saved.project_id), "name": saved.name},
        )
        return saved
