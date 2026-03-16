from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import get_health_service
from app.core.exceptions import ErrorResponse
from app.services.health_service import HealthService

router = APIRouter()


class ComponentStatus(BaseModel):
    status: Literal["ok", "error"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: ComponentStatus
    database: ComponentStatus
    redis: ComponentStatus


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        500: {"model": ErrorResponse},
    },
)
def get_health(health_service: HealthService = Depends(get_health_service)) -> JSONResponse:
    payload = health_service.check()
    http_status = (
        status.HTTP_200_OK
        if payload["status"] == "ok"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=http_status, content=payload)
