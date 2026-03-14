from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_ml_service
from backend.app.modules.ml.schemas import MLResultsWriteRequest, MLResultsWriteResponse
from backend.app.modules.ml.service import MLService

router = APIRouter(tags=["ml"])


@router.post("/ml/results", response_model=MLResultsWriteResponse)
async def write_ml_results(
    payload: MLResultsWriteRequest,
    service: MLService = Depends(get_ml_service),
):
    return service.write_results(payload)
