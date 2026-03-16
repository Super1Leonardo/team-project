from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, Query, Response, status

from backend.app.api.dependencies import get_brandradar_service
from backend.app.modules.brandradar.schemas import (
    ApiEnvelope,
    BrandRadarHealthResponse,
    CollectorRunRequest,
    CollectorSourceStatus,
    CollectorStatusResponse,
    CollectorTriggerResponse,
    MLRunResponse,
    MLQueueResponse,
    MLRemotePredictResponse,
    MLResultsPushRequest,
    MLResultsPushResponse,
    MentionResponse,
    MentionConfidenceThreshold,
    MentionPeriod,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    RawPostResponse,
    ResponseMeta,
    SourceCreateRequest,
    SourceResponse,
    SourceUpdateRequest,
)
from backend.app.modules.brandradar.service import BrandRadarService

router = APIRouter(tags=["brandradar"])


def _envelope(data, *, total: int | None = None, page: int | None = None, page_size: int | None = None):
    meta = None
    if total is not None or page is not None or page_size is not None:
        meta = ResponseMeta(
            total=total,
            page=page,
            page_size=page_size,
        )
    return {
        "data": data,
        "meta": meta,
    }


@router.get("/projects", response_model=ApiEnvelope[list[ProjectResponse]])
async def list_projects(service: BrandRadarService = Depends(get_brandradar_service)):
    projects = await service.list_projects()
    return _envelope(projects, total=len(projects), page=1, page_size=len(projects))


@router.get("/projects/{project_id}", response_model=ApiEnvelope[ProjectResponse])
async def get_project(
    project_id: int,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.get_project(project_id))


@router.post(
    "/projects",
    response_model=ApiEnvelope[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    payload: ProjectCreateRequest,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.create_project(payload))


@router.put("/projects/{project_id}", response_model=ApiEnvelope[ProjectResponse])
@router.patch("/projects/{project_id}", response_model=ApiEnvelope[ProjectResponse])
async def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.update_project(project_id, payload))


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    await service.delete_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/projects/{project_id}/sources",
    response_model=ApiEnvelope[list[SourceResponse]],
)
async def list_sources(
    project_id: int,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    sources = await service.list_sources(project_id)
    return _envelope(sources, total=len(sources), page=1, page_size=len(sources))


@router.get(
    "/projects/{project_id}/sources/{source_id}",
    response_model=ApiEnvelope[SourceResponse],
)
async def get_source(
    project_id: int,
    source_id: int,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.get_source(project_id, source_id))


@router.post(
    "/projects/{project_id}/sources",
    response_model=ApiEnvelope[SourceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    project_id: int,
    payload: SourceCreateRequest,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.create_source(project_id, payload))


@router.put(
    "/projects/{project_id}/sources/{source_id}",
    response_model=ApiEnvelope[SourceResponse],
)
@router.patch(
    "/projects/{project_id}/sources/{source_id}",
    response_model=ApiEnvelope[SourceResponse],
)
async def update_source(
    project_id: int,
    source_id: int,
    payload: SourceUpdateRequest,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.update_source(project_id, source_id, payload))


@router.delete(
    "/projects/{project_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_source(
    project_id: int,
    source_id: int,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    await service.delete_source(project_id, source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/projects/{project_id}/collect",
    response_model=ApiEnvelope[CollectorTriggerResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_collector_once(
    project_id: int,
    payload: CollectorRunRequest = Body(default_factory=CollectorRunRequest),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(
        await service.trigger_collector_run(
            project_id=project_id,
            source_ids=payload.source_ids,
            limit_per_source=payload.limit_per_source,
        )
    )


@router.get(
    "/projects/{project_id}/collector/status",
    response_model=ApiEnvelope[CollectorStatusResponse],
)
async def collector_status(
    project_id: int,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.get_collector_status(project_id=project_id))


@router.get("/ml/queue", response_model=ApiEnvelope[MLQueueResponse])
async def ml_queue(
    limit: int = Query(default=100, ge=1, le=500),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    queue = await service.get_ml_queue(limit=limit)
    return _envelope(queue, total=queue["count"], page=1, page_size=limit)


@router.post("/ml/results", response_model=ApiEnvelope[MLResultsPushResponse])
async def push_ml_results(
    payload: MLResultsPushRequest,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.submit_ml_results(payload))


@router.post("/ml/run", response_model=ApiEnvelope[MLRunResponse])
async def run_ml(
    limit: int = Query(default=100, ge=1, le=500),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.run_local_ml_once(limit=limit))


@router.post("/ml/predict", response_model=ApiEnvelope[MLRemotePredictResponse])
async def predict_with_remote_ml(
    limit: int = Query(default=100, ge=1, le=500),
    persist: bool = Query(default=True),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(await service.predict_with_remote_ml(limit=limit, persist=persist))


@router.get(
    "/projects/{project_id}/raw-posts",
    response_model=ApiEnvelope[list[RawPostResponse]],
)
async def list_raw_posts(
    project_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    raw_posts = await service.list_raw_posts(project_id, limit=limit)
    return _envelope(raw_posts, total=len(raw_posts), page=1, page_size=limit)


@router.get(
    "/projects/{project_id}/mentions",
    response_model=ApiEnvelope[list[MentionResponse]],
)
async def list_mentions(
    project_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=500),
    limit: int | None = Query(default=None, ge=1, le=500),
    confidence: MentionConfidenceThreshold | None = Query(default=None),
    period: MentionPeriod | None = Query(default=None),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    effective_page_size = page_size or limit or 100
    mentions_page = await service.list_mentions(
        project_id,
        page=page,
        page_size=effective_page_size,
        confidence_threshold=confidence.threshold if confidence else None,
        published_after=(datetime.now(UTC) - period.delta) if period else None,
    )
    return _envelope(
        mentions_page["items"],
        total=mentions_page["total"],
        page=page,
        page_size=effective_page_size,
    )


@router.get("/health", response_model=BrandRadarHealthResponse)
async def brandradar_health(
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return await service.get_health()
