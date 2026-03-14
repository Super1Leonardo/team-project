from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_project_service
from app.modules.projects.schemas import ProjectCreate, ProjectRead
from app.modules.projects.service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
async def list_projects(service: ProjectService = Depends(get_project_service)) -> list[ProjectRead]:
    return await service.list()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
) -> ProjectRead:
    return await service.create(payload)
