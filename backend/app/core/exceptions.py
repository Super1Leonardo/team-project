from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    error = "application_error"

    def __init__(self, detail: str, *, payload: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.payload = payload or {}


class ValidationError(AppError):
    status_code = 400
    error = "validation_error"


class NotFoundError(AppError):
    status_code = 404
    error = "not_found"


class ConflictError(AppError):
    status_code = 409
    error = "conflict"


class ExternalServiceUnavailableError(AppError):
    status_code = 503
    error = "external_service_unavailable"
