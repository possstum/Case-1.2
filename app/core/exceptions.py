from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    code: str
    message: str
    correlation_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppException(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class NotFoundException(AppException):
    def __init__(self, message: str = "resource not found") -> None:
        super().__init__(status_code=404, code="not_found", message=message)


class RateLimitExceededException(AppException):
    def __init__(self, message: str = "rate limit exceeded") -> None:
        super().__init__(status_code=429, code="rate_limit_exceeded", message=message)


class ServiceUnavailableException(AppException):
    def __init__(
        self,
        message: str = "service unavailable",
        *,
        code: str = "service_unavailable",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            status_code=503,
            code=code,
            message=message,
            details=details,
        )


def _get_correlation_id(request: Request) -> Optional[str]:
    return getattr(request.state, "correlation_id", None)


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            correlation_id=_get_correlation_id(request),
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=422,
            code="validation_error",
            message="request validation failed",
            details={"errors": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase.lower()
        details = None if isinstance(exc.detail, str) else {"detail": exc.detail}
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code="http_error",
            message=message,
            details=details,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("unhandled_exception", exc_info=exc)
        return _error_response(
            request=request,
            status_code=500,
            code="internal_server_error",
            message="internal server error",
        )


AppError = AppException
NotFoundError = NotFoundException
RateLimitExceededError = RateLimitExceededException
ServiceUnavailableError = ServiceUnavailableException
