178.154.216.255from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi.encoders import jsonable_encoder

from backend.app.core.config import Settings
from backend.app.core.exceptions import ExternalMLServiceError


class ExternalMLGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def predict_url(self) -> str:
        base = self.settings.external_ml_base_url.rstrip("/") + "/"
        path = self.settings.external_ml_predict_path.lstrip("/")
        return urljoin(base, path)

    async def predict(self, items: list[dict[str, Any]]) -> Any:
        payload = {
            "items": jsonable_encoder(items),
        }

        timeout = httpx.Timeout(self.settings.external_ml_timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.predict_url, json=payload)
        except httpx.HTTPError as exc:
            raise ExternalMLServiceError(
                f"External ML request to {self.predict_url} failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise ExternalMLServiceError(
                f"External ML service returned {response.status_code}: {detail}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ExternalMLServiceError(
                "External ML service returned a non-JSON response."
            ) from exc
