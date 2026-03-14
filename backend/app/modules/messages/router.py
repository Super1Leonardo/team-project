from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import get_messages_service
from backend.app.modules.messages.schemas import StoredMessagesResponse
from backend.app.modules.messages.service import MessagesService

router = APIRouter(tags=["messages"])


@router.get("/messages/stored", response_model=StoredMessagesResponse)
async def get_stored_messages(
    limit: int = Query(default=100, ge=1, le=1000),
    source_type: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    service: MessagesService = Depends(get_messages_service),
):
    return service.get_stored_messages(
        limit=limit,
        source_type=source_type,
        channel=channel,
    )
