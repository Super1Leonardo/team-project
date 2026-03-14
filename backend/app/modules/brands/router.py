from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_brand_service
from app.modules.brands.schemas import BrandCreate, BrandRead, BrandUpdate
from app.modules.brands.service import BrandService

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("", response_model=list[BrandRead])
async def list_brands(
    project_id: uuid.UUID | None = Query(default=None),
    service: BrandService = Depends(get_brand_service),
) -> list[BrandRead]:
    return await service.list(project_id=project_id)


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
async def create_brand(
    payload: BrandCreate,
    service: BrandService = Depends(get_brand_service),
) -> BrandRead:
    return await service.create(payload)


@router.put("/{brand_id}", response_model=BrandRead)
async def update_brand(
    brand_id: uuid.UUID,
    payload: BrandUpdate,
    service: BrandService = Depends(get_brand_service),
) -> BrandRead:
    return await service.update(brand_id, payload)
