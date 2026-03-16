from datetime import UTC, datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, Query, Response, status

from backend.app.api.dependencies import get_brandradar_service
from backend.app.modules.brandradar.schemas import (
    ApiEnvelope,
    BrandRadarHealthResponse,
    CollectorRunRequest,
    CollectorStatusResponse,
    CollectorTriggerResponse,
    MLRunResponse,
    MLQueueResponse,
    MLRemotePredictResponse,
    MLResultsPushRequest,
    MLResultsPushResponse,
    MentionClusterResponse,
    MentionResponse,
    MentionConfidenceThreshold,
    MentionPeriod,
    MentionResolvedUpdateRequest,
    MentionSentiment,
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


def _get_mock_mentions(project_id: int, limit: int = 100) -> list[dict]:
    """Generate mock mentions for testing when database is empty."""
    now = datetime.now(timezone.utc)

    mock_data = [
        {
            "id": 1,
            "raw_post_id": 1,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg001",
            "url": "https://t.me/durov/101",
            "title": "Сбербанк запускает новый сервис для малого бизнеса",
            "text": "Сбербанк запускает новый сервис для малого бизнеса",
            "author": "Иван Иванов",
            "published_at": now - timedelta(days=1),
            "collected_at": now - timedelta(days=1),
            "relevance_score": 0.85,
            "relevance_label": "relevant",
            "sentiment_score": 0.7,
            "sentiment_label": "positive",
            "has_risk_words": False,
            "dedup_group_id": 1,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=12),
        },
        {
            "id": 2,
            "raw_post_id": 2,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg002",
            "url": "https://t.me/durov/102",
            "title": "Сбербанк оштрафован на миллиард рублей",
            "text": "Сбербанк оштрафован на миллиард рублей",
            "author": "Петр Петров",
            "published_at": now - timedelta(days=2),
            "collected_at": now - timedelta(days=2),
            "relevance_score": 0.95,
            "relevance_label": "relevant",
            "sentiment_score": 0.2,
            "sentiment_label": "negative",
            "has_risk_words": True,
            "dedup_group_id": 2,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=36),
        },
        {
            "id": 3,
            "raw_post_id": 3,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg003",
            "url": "https://t.me/durov/103",
            "title": "Sberbank объявил о росте акций на 5%",
            "text": "Sberbank объявил о росте акций на 5%",
            "author": "Анна Сидорова",
            "published_at": now - timedelta(days=3),
            "collected_at": now - timedelta(days=3),
            "relevance_score": 0.75,
            "relevance_label": "relevant",
            "sentiment_score": 0.6,
            "sentiment_label": "positive",
            "has_risk_words": False,
            "dedup_group_id": 3,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=48),
        },
        {
            "id": 4,
            "raw_post_id": 4,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg004",
            "url": "https://t.me/durov/104",
            "title": "В Сбербанке произошёл сбой в работе приложения",
            "text": "В Сбербанке произошёл сбой в работе приложения",
            "author": "Михаил Михайлов",
            "published_at": now - timedelta(days=4),
            "collected_at": now - timedelta(days=4),
            "relevance_score": 0.88,
            "relevance_label": "relevant",
            "sentiment_score": 0.3,
            "sentiment_label": "negative",
            "has_risk_words": True,
            "dedup_group_id": 4,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=60),
        },
        {
            "id": 5,
            "raw_post_id": 5,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg005",
            "url": "https://t.me/durov/105",
            "title": "Сбербанк проводит конференцию для инвесторов",
            "text": "Сбербанк проводит конференцию для инвесторов",
            "author": "Елена Козлова",
            "published_at": now - timedelta(days=5),
            "collected_at": now - timedelta(days=5),
            "relevance_score": 0.7,
            "relevance_label": "relevant",
            "sentiment_score": 0.5,
            "sentiment_label": "neutral",
            "has_risk_words": False,
            "dedup_group_id": 5,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=72),
        },
        {
            "id": 6,
            "raw_post_id": 6,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg006",
            "url": "https://t.me/durov/106",
            "title": "Sberbank снова в топе банков по версии Forbes",
            "text": "Sberbank снова в топе банков по версии Forbes",
            "author": "Дмитрий Волков",
            "published_at": now - timedelta(days=6),
            "collected_at": now - timedelta(days=6),
            "relevance_score": 0.92,
            "relevance_label": "relevant",
            "sentiment_score": 0.8,
            "sentiment_label": "positive",
            "has_risk_words": False,
            "dedup_group_id": 6,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=84),
        },
        {
            "id": 7,
            "raw_post_id": 7,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg007",
            "url": "https://t.me/durov/107",
            "title": "Клиенты Сбербанка жалуются на качество обслуживания",
            "text": "Клиенты Сбербанка жалуются на качество обслуживания",
            "author": "Ольга Новикова",
            "published_at": now - timedelta(hours=6),
            "collected_at": now - timedelta(hours=6),
            "relevance_score": 0.78,
            "relevance_label": "relevant",
            "sentiment_score": 0.35,
            "sentiment_label": "negative",
            "has_risk_words": False,
            "dedup_group_id": 7,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=3),
        },
        {
            "id": 8,
            "raw_post_id": 8,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg008",
            "url": "https://t.me/durov/108",
            "title": "Сбербанк представил новый продукт для бизнеса",
            "text": "Сбербанк представил новый продукт для бизнеса",
            "author": "Сергей Смирнов",
            "published_at": now - timedelta(hours=12),
            "collected_at": now - timedelta(hours=12),
            "relevance_score": 0.82,
            "relevance_label": "relevant",
            "sentiment_score": 0.65,
            "sentiment_label": "positive",
            "has_risk_words": False,
            "dedup_group_id": 8,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=8),
        },
        {
            "id": 9,
            "raw_post_id": 9,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg009",
            "url": "https://t.me/durov/109",
            "title": "Sberbank: отчётность за квартал превзошла ожидания",
            "text": "Sberbank: отчётность за квартал превзошла ожидания",
            "author": "Наталья Морозова",
            "published_at": now - timedelta(hours=18),
            "collected_at": now - timedelta(hours=18),
            "relevance_score": 0.9,
            "relevance_label": "relevant",
            "sentiment_score": 0.75,
            "sentiment_label": "positive",
            "has_risk_words": False,
            "dedup_group_id": 9,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=10),
        },
        {
            "id": 10,
            "raw_post_id": 10,
            "project_id": project_id,
            "source_id": 1,
            "source_type": "telegram",
            "external_id": "msg010",
            "url": "https://t.me/durov/110",
            "title": "В Сбербанке обнаружена утечка данных клиентов",
            "text": "В Сбербанке обнаружена утечка данных клиентов",
            "author": "Алексей Кузнецов",
            "published_at": now - timedelta(days=1, hours=12),
            "collected_at": now - timedelta(days=1, hours=12),
            "relevance_score": 0.98,
            "relevance_label": "relevant",
            "sentiment_score": 0.1,
            "sentiment_label": "negative",
            "has_risk_words": True,
            "dedup_group_id": 10,
            "is_primary": True,
            "resolved": False,
            "processed_at": now - timedelta(hours=20),
        },
    ]

    return mock_data[:limit]


def _envelope(
    data,
    *,
    total: int | None = None,
    page: int | None = None,
    page_size: int | None = None,
):
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
            lookback_days=payload.lookback_days,
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
    sentiment: MentionSentiment | None = Query(default=None),
    primary_only: bool = Query(default=False),
    relevant_only: bool = Query(default=False),
    include_total: bool = Query(default=True),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    effective_page_size = page_size or limit or 100
    mentions_page = await service.list_mentions(
        project_id,
        page=page,
        page_size=effective_page_size,
        confidence_threshold=confidence.threshold if confidence else None,
        published_after=(datetime.now(UTC) - period.delta) if period else None,
        sentiment_label=sentiment.value if sentiment else None,
        primary_only=primary_only,
        relevant_only=relevant_only,
        include_total=include_total,
    )
    return _envelope(
        mentions_page["items"],
        total=mentions_page["total"] if include_total else None,
        page=page,
        page_size=effective_page_size,
    )


@router.post(
    "/projects/{project_id}/mentions/{mention_id}/resolved",
    response_model=ApiEnvelope[MentionResponse],
)
async def update_mention_resolved(
    project_id: int,
    mention_id: int,
    payload: MentionResolvedUpdateRequest,
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return _envelope(
        await service.update_mention_resolved(
            project_id,
            mention_id,
            resolved=payload.resolved,
        )
    )


@router.get(
    "/feed",
    response_model=ApiEnvelope[list[MentionResponse]],
)
async def list_default_feed(
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=500),
    limit: int | None = Query(default=None, ge=1, le=500),
    confidence: MentionConfidenceThreshold | None = Query(default=None),
    period: MentionPeriod | None = Query(default=None),
    sentiment: MentionSentiment | None = Query(default=None),
    primary_only: bool = Query(default=True),
    relevant_only: bool = Query(default=True),
    include_total: bool = Query(default=False),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    effective_page_size = page_size or limit or 100
    mentions_page = await service.list_default_mentions(
        page=page,
        page_size=effective_page_size,
        confidence_threshold=confidence.threshold if confidence else None,
        published_after=(datetime.now(UTC) - period.delta) if period else None,
        sentiment_label=sentiment.value if sentiment else None,
        primary_only=primary_only,
        relevant_only=relevant_only,
        include_total=include_total,
    )
    return _envelope(
        mentions_page["items"],
        total=mentions_page["total"] if include_total else None,
        page=page,
        page_size=effective_page_size,
    )


@router.get(
    "/projects/{project_id}/clusters",
    response_model=ApiEnvelope[list[MentionClusterResponse]],
)
async def list_clusters(
    project_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=500),
    limit: int | None = Query(default=None, ge=1, le=500),
    confidence: MentionConfidenceThreshold | None = Query(default=None),
    period: MentionPeriod | None = Query(default=None),
    sentiment: MentionSentiment | None = Query(default=None),
    service: BrandRadarService = Depends(get_brandradar_service),
):
    effective_page_size = page_size or limit or 100
    clusters_page = await service.list_clusters(
        project_id,
        page=page,
        page_size=effective_page_size,
        confidence_threshold=confidence.threshold if confidence else None,
        published_after=(datetime.now(UTC) - period.delta) if period else None,
        sentiment_label=sentiment.value if sentiment else None,
    )
    return _envelope(
        clusters_page["items"],
        total=clusters_page["total"],
        page=page,
        page_size=effective_page_size,
    )


@router.get("/health", response_model=BrandRadarHealthResponse)
async def brandradar_health(
    service: BrandRadarService = Depends(get_brandradar_service),
):
    return await service.get_health()
