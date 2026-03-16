from __future__ import annotations

from pydantic import BaseModel

from app.api.schemas.jobs import SyncJobResponse


class SyncEnqueueResponse(BaseModel):
    created: bool
    job: SyncJobResponse
