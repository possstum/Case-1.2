from __future__ import annotations

from contextvars import ContextVar
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.core.config import Settings

correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    return correlation_id_ctx.get()


def install_http_middleware(app: FastAPI, settings: Settings) -> None:
    header_name = settings.correlation_id_header

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next) -> Response:
        correlation_id = request.headers.get(header_name) or uuid4().hex
        token = correlation_id_ctx.set(correlation_id)
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
        finally:
            correlation_id_ctx.reset(token)

        response.headers[header_name] = correlation_id
        return response
