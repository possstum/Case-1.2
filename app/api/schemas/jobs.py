from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SyncJobResponse(BaseModel):
    id: str
    kind: str
    target_id: str
    status: str
    queue_name: str
    attempts: int
    payload_json: dict[str, Any] = Field(default_factory=dict)
    result_json: Optional[dict[str, Any]] = None
    error_json: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
