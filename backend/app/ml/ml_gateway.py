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
        self._predict_client: httpx.AsyncClient | None = None
        self._health_client: httpx.AsyncClient | None = None

    @property
    def predict_url(self) -> str:
        base = self.settings.external_ml_base_url.rstrip("/") + "/"
        path = self.settings.external_ml_predict_path.lstrip("/")
        return urljoin(base, path)

    @property
    def health_url(self) -> str:
        base = self.settings.external_ml_base_url.rstrip("/") + "/"
        path = self.settings.external_ml_health_path.lstrip("/")
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

    @property
    def predict_params(self) -> dict[str, int] | None:
        predict_path = self.settings.external_ml_predict_path.casefold()
        if "with_tokens" not in predict_path:
            return None

        top_k = int(self.settings.external_ml_top_k_tokens)
        if top_k <= 0:
            return None
        return {"top_k": top_k}

    def _build_async_client(self, *, timeout: httpx.Timeout) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
            ),
        )

    def _get_predict_client(self) -> httpx.AsyncClient:
        client = self._predict_client
        if client is None or bool(getattr(client, "is_closed", False)):
            client = self._build_async_client(timeout=self.predict_timeout)
            self._predict_client = client
        return client

    def _get_health_client(self) -> httpx.AsyncClient:
        client = self._health_client
        if client is None or bool(getattr(client, "is_closed", False)):
            client = self._build_async_client(timeout=self.health_timeout)
            self._health_client = client
        return client

    async def aclose(self) -> None:
        for attribute_name in ("_predict_client", "_health_client"):
            client = getattr(self, attribute_name)
            if client is None:
                continue
            close = getattr(client, "aclose", None)
            if callable(close):
                await close()
            setattr(self, attribute_name, None)

    async def predict(self, items: list[dict[str, Any]]) -> Any:
        payload = {
            "items": jsonable_encoder(
                [
                    {
                        "text": item.get("text", ""),
                        "company": item.get("company", ""),
                    }
                    for item in items
                ]
            ),
        }

        try:
            response = await self._get_predict_client().post(
                self.predict_url,
                json=payload,
                params=self.predict_params,
            )
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
        try:
            response = await self._get_health_client().get(self.health_url)
        except httpx.HTTPError as exc:
            return {
                "status": "unhealthy",
                "url": self.health_url,
                "error": f"External ML health request to {self.health_url} failed: {exc}",
            }

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            return {
                "status": "unhealthy",
                "url": self.health_url,
                "error": f"External ML health probe returned {response.status_code}: {detail}",
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "status": "healthy",
                "url": self.health_url,
                "error": None,
            }

        if isinstance(payload, dict):
            raw_status = str(payload.get("status", "")).strip().casefold()
            if raw_status in {"", "ok", "healthy"}:
                return {
                    "status": "healthy",
                    "url": self.health_url,
                    "error": None,
                }
            return {
                "status": "unhealthy",
                "url": self.health_url,
                "error": f"External ML health probe returned unexpected status: {payload.get('status')}",
            }

        return {
            "status": "healthy",
            "url": self.health_url,
            "error": None,
        }
