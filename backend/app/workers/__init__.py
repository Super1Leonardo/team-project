from __future__ import annotations

__all__ = ["CollectorWorker", "MLWorker"]


def __getattr__(name: str):
    if name == "CollectorWorker":
        from backend.app.workers.collector_worker import CollectorWorker

        return CollectorWorker
    if name == "MLWorker":
        from backend.app.workers.ml_worker import MLWorker

        return MLWorker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
