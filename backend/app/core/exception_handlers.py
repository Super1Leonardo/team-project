from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.exceptions import (
    DomainValidationError,
    ExternalMLServiceError,
    FeatureNotImplementedError,
    ResourceNotFoundError,
)
from backend.app.infra.db.clickhouse import ClickHouseMessageStoreError
from backend.app.infra.gateways.telegram_gateway import TelegramServiceError


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


async def _handle_domain_validation(_: Request, exc: DomainValidationError) -> JSONResponse:
    return _error_response(400, "VALIDATION_ERROR", str(exc))


async def _handle_feature_not_implemented(
    _: Request,
    exc: FeatureNotImplementedError,
) -> JSONResponse:
    return _error_response(501, "NOT_IMPLEMENTED", str(exc))


async def _handle_not_found(_: Request, exc: ResourceNotFoundError) -> JSONResponse:
    return _error_response(404, "NOT_FOUND", str(exc))


async def _handle_telegram_bad_request(
    _: Request,
    exc: TelegramServiceError,
) -> JSONResponse:
    return _error_response(400, "BAD_REQUEST", str(exc))


async def _handle_clickhouse_error(
    _: Request,
    exc: ClickHouseMessageStoreError,
) -> JSONResponse:
    return _error_response(503, "SERVICE_UNAVAILABLE", str(exc))


async def _handle_external_ml_error(
    _: Request,
    exc: ExternalMLServiceError,
) -> JSONResponse:
    return _error_response(503, "SERVICE_UNAVAILABLE", str(exc))


async def _handle_request_validation(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else None
    message = first_error.get("msg") if first_error else "Request validation failed."
    return _error_response(422, "VALIDATION_ERROR", message)


async def _handle_http_exception(
    _: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    return _error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _handle_request_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(DomainValidationError, _handle_domain_validation)
    app.add_exception_handler(ResourceNotFoundError, _handle_not_found)
    app.add_exception_handler(
        FeatureNotImplementedError,
        _handle_feature_not_implemented,
    )
    app.add_exception_handler(
        TelegramServiceError,
        _handle_telegram_bad_request,
    )
    app.add_exception_handler(
        ClickHouseMessageStoreError,
        _handle_clickhouse_error,
    )
    app.add_exception_handler(
        ExternalMLServiceError,
        _handle_external_ml_error,
    )
