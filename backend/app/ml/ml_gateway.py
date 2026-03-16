from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi.encoders import jsonable_encoder

from backend.app.core.config import Settings
from backend.app.core.exceptions import ExternalMLRequestError, ExternalMLResponseError


class ExternalMLGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def predict_url(self) -> str:
        base = self.settings.external_ml_base_url.rstrip("/") + "/"
        path = self.settings.external_ml_predict_path.lstrip("/")
        return urljoin(base, path)

    @property
    def predict_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            self.settings.external_ml_timeout_seconds,
            connect=self.settings.external_ml_connect_timeout_seconds,
        )

    @property
    def health_timeout(self) -> httpx.Timeout:
        timeout_seconds = self.settings.external_ml_health_timeout_seconds
        connect_timeout_seconds = min(
            self.settings.external_ml_connect_timeout_seconds,
            timeout_seconds,
        )
        return httpx.Timeout(
            timeout_seconds,
            connect=connect_timeout_seconds,
        )

    async def predict(self, items: list[dict[str, Any]]) -> Any:
        payload = {
            "items": jsonable_encoder(
                [{"text": item.get("text", "")} for item in items]
            ),
        }

        try:
            async with httpx.AsyncClient(timeout=self.predict_timeout) as client:
                response = await client.post(self.predict_url, json=payload)
        except httpx.HTTPError as exc:
            raise ExternalMLRequestError(
                f"External ML request to {self.predict_url} failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise ExternalMLRequestError(
                f"External ML service returned {response.status_code}: {detail}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ExternalMLResponseError(
                "External ML service returned a non-JSON response."
            ) from exc

    async def get_health_status(self) -> dict[str, Any]:
        payload = {"items": []}

        try:
            async with httpx.AsyncClient(timeout=self.health_timeout) as client:
                response = await client.post(self.predict_url, json=payload)
        except httpx.HTTPError as exc:
            return {
                "status": "unhealthy",
                "url": self.predict_url,
                "error": f"External ML request to {self.predict_url} failed: {exc}",
            }

        if response.is_success or response.status_code in {400, 422}:
            return {
                "status": "healthy",
                "url": self.predict_url,
                "error": None,
            }

        detail = response.text.strip() or response.reason_phrase
        return {
            "status": "unhealthy",
            "url": self.predict_url,
            "error": f"External ML health probe returned {response.status_code}: {detail}",
        }
