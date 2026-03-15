from __future__ import annotations

__all__ = [
    "ExternalMLGateway",
    "MLResultNormalizer",
]


def __getattr__(name: str):
    if name == "ExternalMLGateway":
        from backend.app.ml.ml_gateway import ExternalMLGateway

        return ExternalMLGateway
    if name == "MLResultNormalizer":
        from backend.app.ml.normalizer import MLResultNormalizer

        return MLResultNormalizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
