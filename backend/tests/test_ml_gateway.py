from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

import httpx

from backend.app.core.config import Settings
from backend.app.ml.ml_gateway import ExternalMLGateway


class _RecordingAsyncClient:
    instances: list["_RecordingAsyncClient"] = []
    response = httpx.Response(200, json={"results": []})

    def __init__(self, *, timeout: httpx.Timeout, **_: object):
        self.timeout = timeout
        self.post_calls: list[tuple[str, dict]] = []
        self.get_calls: list[str] = []
        self.__class__.instances.append(self)

    async def __aenter__(self) -> "_RecordingAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def aclose(self) -> None:
        return None

    async def post(self, url: str, json: dict, params: dict | None = None) -> httpx.Response:
        self.post_calls.append((url, {"json": json, "params": params}))
        return self.__class__.response

    async def get(self, url: str) -> httpx.Response:
        self.get_calls.append(url)
        return self.__class__.response


class ExternalMLGatewayTests(unittest.TestCase):
    def test_predict_uses_fast_connect_timeout(self) -> None:
        settings = Settings(
            external_ml_base_url="http://ml.example",
            external_ml_predict_path="/predict",
            external_ml_top_k_tokens=7,
            external_ml_timeout_seconds=60,
            external_ml_connect_timeout_seconds=3,
        )
        gateway = ExternalMLGateway(settings)
        _RecordingAsyncClient.instances.clear()
        _RecordingAsyncClient.response = httpx.Response(200, json={"results": []})

        with patch("backend.app.ml.ml_gateway.httpx.AsyncClient", _RecordingAsyncClient):
            asyncio.run(
                gateway.predict(
                    [
                        {
                            "raw_post_id": 1,
                            "text": "brand update",
                            "company": "Brand Radar",
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
            [
                (
                    "http://ml.example/predict",
                    {
                        "json": {"items": [{"text": "brand update", "company": "Brand Radar"}]},
                        "params": None,
                    },
                )
            ],
        )

    def test_predict_passes_top_k_only_for_token_endpoint(self) -> None:
        settings = Settings(
            external_ml_base_url="http://ml.example",
            external_ml_predict_path="/analyze_with_tokens_batch",
            external_ml_top_k_tokens=7,
            external_ml_timeout_seconds=60,
            external_ml_connect_timeout_seconds=3,
        )
        gateway = ExternalMLGateway(settings)
        _RecordingAsyncClient.instances.clear()
        _RecordingAsyncClient.response = httpx.Response(200, json={"results": []})

        with patch("backend.app.ml.ml_gateway.httpx.AsyncClient", _RecordingAsyncClient):
            asyncio.run(
                gateway.predict(
                    [
                        {
                            "raw_post_id": 1,
                            "text": "brand update",
                            "company": "Brand Radar",
                            "keywords": ["brand"],
                        }
                    ]
                )
            )

        client = _RecordingAsyncClient.instances[-1]
        self.assertEqual(
            client.post_calls,
            [
                (
                    "http://ml.example/analyze_with_tokens_batch",
                    {
                        "json": {"items": [{"text": "brand update", "company": "Brand Radar"}]},
                        "params": {"top_k": 7},
                    },
                )
            ],
        )

    def test_health_probe_uses_short_timeout_and_returns_healthy_on_ok_status(self) -> None:
        settings = Settings(
            external_ml_base_url="http://ml.example",
            external_ml_predict_path="/predict",
            external_ml_health_path="/health",
            external_ml_health_timeout_seconds=2,
            external_ml_connect_timeout_seconds=3,
        )
        gateway = ExternalMLGateway(settings)
        _RecordingAsyncClient.instances.clear()
        _RecordingAsyncClient.response = httpx.Response(
            200,
            json={"status": "ok"},
        )

        with patch("backend.app.ml.ml_gateway.httpx.AsyncClient", _RecordingAsyncClient):
            result = asyncio.run(gateway.get_health_status())

        client = _RecordingAsyncClient.instances[-1]
        self.assertEqual(client.timeout.connect, 2)
        self.assertEqual(client.timeout.read, 2)
        self.assertEqual(client.post_calls, [])
        self.assertEqual(client.get_calls, ["http://ml.example/health"])
        self.assertEqual(
            result,
            {
                "status": "healthy",
                "url": "http://ml.example/health",
                "error": None,
            },
        )
