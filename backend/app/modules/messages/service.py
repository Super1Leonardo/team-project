from backend.app.modules.messages.repository import MessagesRepository
from backend.app.modules.messages.schemas import StoredMessagesResponse


class MessagesService:
    def __init__(self, repository: MessagesRepository):
        self.repository = repository

    def get_stored_messages(
        self,
        limit: int,
        source_type: str | None,
        channel: str | None,
    ) -> StoredMessagesResponse:
        return self.repository.fetch_messages(
            limit=limit,
            source_type=source_type,
            channel=channel,
        )
