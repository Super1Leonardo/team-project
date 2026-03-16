from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

import httpx

from backend.app.core.config import Settings
from backend.app.ml.ml_gateway import ExternalMLGateway


class _RecordingAsyncClient:
    instances: list["_RecordingAsyncClient"] = []
    response = httpx.Response(200, json={"items": []})

    def __init__(self, *, timeout: httpx.Timeout):
        self.timeout = timeout
        self.post_calls: list[tuple[str, dict]] = []
        self.__class__.instances.append(self)

    async def __aenter__(self) -> "_RecordingAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, json: dict) -> httpx.Response:
        self.post_calls.append((url, json))
        return self.__class__.response


class ExternalMLGatewayTests(unittest.TestCase):
    def test_predict_uses_fast_connect_timeout(self) -> None:
        settings = Settings(
            external_ml_base_url="http://ml.example",
            external_ml_predict_path="/predict",
            external_ml_timeout_seconds=60,
            external_ml_connect_timeout_seconds=3,
        )
        gateway = ExternalMLGateway(settings)
        _RecordingAsyncClient.instances.clear()
        _RecordingAsyncClient.response = httpx.Response(200, json={"items": []})

        with patch("backend.app.ml.ml_gateway.httpx.AsyncClient", _RecordingAsyncClient):
            asyncio.run(
                gateway.predict(
                    [
                        {
                            "raw_post_id": 1,
                            "text": "brand update",
                            "keywords": ["brand"],
                        }
                    ]
                )
            )

        client = _RecordingAsyncClient.instances[-1]
        self.assertEqual(client.timeout.connect, 3)
        self.assertEqual(client.timeout.read, 60)
        self.assertEqual(
            client.post_calls,
            [("http://ml.example/predict", {"items": [{"text": "brand update"}]})],
        )

    def test_health_probe_uses_short_timeout_and_returns_healthy_on_422(self) -> None:
        settings = Settings(
            external_ml_base_url="http://ml.example",
            external_ml_predict_path="/predict",
            external_ml_health_timeout_seconds=2,
            external_ml_connect_timeout_seconds=3,
        )
        gateway = ExternalMLGateway(settings)
        _RecordingAsyncClient.instances.clear()
        _RecordingAsyncClient.response = httpx.Response(
            422,
            json={"detail": "items required"},
        )

        with patch("backend.app.ml.ml_gateway.httpx.AsyncClient", _RecordingAsyncClient):
            result = asyncio.run(gateway.get_health_status())

        client = _RecordingAsyncClient.instances[-1]
        self.assertEqual(client.timeout.connect, 2)
        self.assertEqual(client.timeout.read, 2)
        self.assertEqual(
            client.post_calls,
            [("http://ml.example/predict", {"items": []})],
        )
        self.assertEqual(
            result,
            {
                "status": "healthy",
                "url": "http://ml.example/predict",
                "error": None,
            },
        )
