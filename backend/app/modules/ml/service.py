from backend.app.modules.ml.repository import MLResultsRepository
from backend.app.modules.ml.schemas import MLResultsWriteRequest, MLResultsWriteResponse


class MLService:
    def __init__(self, repository: MLResultsRepository):
        self.repository = repository

    def write_results(self, payload: MLResultsWriteRequest) -> MLResultsWriteResponse:
        stored_count = self.repository.save_results(payload.results)
        offset_updated = payload.offset is not None

        if payload.offset is not None:
            self.repository.update_offset(payload.offset)

        return MLResultsWriteResponse(
            stored_count=stored_count,
            offset_updated=offset_updated,
            consumer_name=payload.offset.consumer_name if payload.offset else None,
            message="ML results stored in Postgres.",
        )
