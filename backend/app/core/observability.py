from __future__ import annotations

import asyncio
import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestMetricsSnapshot:
    window_seconds: int
    requests: int
    errors: int
    rps: float
    rpm: float
    error_rate_percent: float
    avg_latency_ms: float
    p95_latency_ms: float
    inflight: int
    uptime_seconds: float


class RequestMetricsTracker:
    def __init__(
        self,
        *,
        window_seconds: int = 60,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive.")

        self.window_seconds = window_seconds
        self._clock = clock or time.monotonic
        self._started_at = self._clock()
        self._observations: deque[tuple[float, float, bool]] = deque()
        self._inflight = 0
        self._lock = threading.Lock()

    def request_started(self) -> None:
        with self._lock:
            self._inflight += 1

    def request_finished(self, *, status_code: int, duration_ms: float) -> None:
        now = self._clock()
        with self._lock:
            self._prune_locked(now)
            self._observations.append((now, duration_ms, status_code >= 500))
            self._inflight = max(0, self._inflight - 1)

    def snapshot(self) -> RequestMetricsSnapshot:
        now = self._clock()
        with self._lock:
            self._prune_locked(now)
            observations = list(self._observations)
            inflight = self._inflight

        requests = len(observations)
        errors = sum(1 for _, _, is_error in observations if is_error)
        latencies = sorted(duration_ms for _, duration_ms, _ in observations)
        avg_latency_ms = (
            sum(duration_ms for _, duration_ms, _ in observations) / requests
            if requests
            else 0.0
        )
        p95_latency_ms = _percentile(latencies, 95.0)
        uptime_seconds = max(0.0, now - self._started_at)
        denominator = max(1e-6, min(float(self.window_seconds), uptime_seconds or 1e-6))
        rps = requests / denominator
        return RequestMetricsSnapshot(
            window_seconds=self.window_seconds,
            requests=requests,
            errors=errors,
            rps=rps,
            rpm=rps * 60.0,
            error_rate_percent=(errors / requests * 100.0) if requests else 0.0,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            inflight=inflight,
            uptime_seconds=uptime_seconds,
        )

    def _prune_locked(self, now: float) -> None:
        min_timestamp = now - self.window_seconds
        while self._observations and self._observations[0][0] < min_timestamp:
            self._observations.popleft()


def install_request_metrics_middleware(
    app: FastAPI,
    *,
    tracker: RequestMetricsTracker,
    slow_request_threshold_ms: float,
) -> None:
    app.state.request_metrics_tracker = tracker

    @app.middleware("http")
    async def request_metrics_middleware(request: Request, call_next):
        tracker.request_started()
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - started_at) * 1000.0
            tracker.request_finished(
                status_code=status_code,
                duration_ms=duration_ms,
            )
            if status_code >= 500 or duration_ms >= slow_request_threshold_ms:
                client_host = request.client.host if request.client else "-"
                logger.warning(
                    "HTTP request completed method=%s path=%s status=%s duration_ms=%.1f client=%s",
                    request.method,
                    request.url.path,
                    status_code,
                    duration_ms,
                    client_host,
                )


async def log_request_metrics_forever(
    *,
    stop_event: asyncio.Event,
    tracker: RequestMetricsTracker,
    interval_seconds: float,
) -> None:
    if interval_seconds <= 0:
        return

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            break
        except asyncio.TimeoutError:
            snapshot = tracker.snapshot()
            logger.info(
                (
                    "HTTP metrics window_s=%s requests=%s rps=%.2f rpm=%.1f "
                    "errors=%s error_rate=%.1f%% avg_ms=%.1f p95_ms=%.1f "
                    "inflight=%s uptime_s=%.0f"
                ),
                snapshot.window_seconds,
                snapshot.requests,
                snapshot.rps,
                snapshot.rpm,
                snapshot.errors,
                snapshot.error_rate_percent,
                snapshot.avg_latency_ms,
                snapshot.p95_latency_ms,
                snapshot.inflight,
                snapshot.uptime_seconds,
            )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]

    rank = (percentile / 100.0) * (len(values) - 1)
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    lower_value = values[lower_index]
    upper_value = values[upper_index]
    if lower_index == upper_index:
        return lower_value
    fraction = rank - lower_index
    return lower_value + (upper_value - lower_value) * fraction
