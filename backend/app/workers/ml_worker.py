from __future__ import annotations

import asyncio
from typing import Any

from backend.app.ml.pipeline import MLPipeline


class MLWorker:
    def __init__(
        self,
        pipeline: MLPipeline,
        *,
        batch_size: int = 100,
        idle_sleep_seconds: float = 15.0,
    ):
        self.pipeline = pipeline
        self.batch_size = batch_size
        self.idle_sleep_seconds = idle_sleep_seconds

    async def run_once(self) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.pipeline.process_batch,
            self.batch_size,
        )

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        event = stop_event or asyncio.Event()

        while not event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(event.wait(), timeout=self.idle_sleep_seconds)
            except TimeoutError:
                continue
