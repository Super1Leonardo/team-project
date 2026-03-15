from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_sources_service
from backend.app.modules.sources.schemas import (
    AppConfigResponse,
    RssFeedsResponse,
    RssFeedsSelectionRequest,
    SourceSelectionRequest,
    SourceSelectionResponse,
    TelegramChannelsResponse,
    TelegramChannelsSelectionRequest,
)
from backend.app.modules.sources.service import SourcesService

router = APIRouter(tags=["sources"])


@router.get("/app-config", response_model=AppConfigResponse)
async def app_config(service: SourcesService = Depends(get_sources_service)):
    return service.get_app_config()


@router.get("/parser/source", response_model=SourceSelectionResponse)
async def get_parser_source(service: SourcesService = Depends(get_sources_service)):
    return service.get_source_selection()


@router.post("/parser/source", response_model=SourceSelectionResponse)
async def set_parser_source(
    payload: SourceSelectionRequest,
    service: SourcesService = Depends(get_sources_service),
):
    return service.set_source_selection(payload)


@router.get("/channels", response_model=TelegramChannelsResponse)
async def list_channels(service: SourcesService = Depends(get_sources_service)):
    return service.get_telegram_channels()


@router.get("/parser/telegram/channels", response_model=TelegramChannelsResponse)
async def get_telegram_channels(service: SourcesService = Depends(get_sources_service)):
    return service.get_telegram_channels()


@router.post("/parser/telegram/channels", response_model=TelegramChannelsResponse)
async def set_telegram_channels(
    payload: TelegramChannelsSelectionRequest,
    service: SourcesService = Depends(get_sources_service),
):
    return service.set_telegram_channels(payload)


@router.get("/parser/rss/feeds", response_model=RssFeedsResponse)
async def get_rss_feeds(service: SourcesService = Depends(get_sources_service)):
    return service.get_rss_feeds()


@router.post("/parser/rss/feeds", response_model=RssFeedsResponse)
async def set_rss_feeds(
    payload: RssFeedsSelectionRequest,
    service: SourcesService = Depends(get_sources_service),
):
    return service.set_rss_feeds(payload)
