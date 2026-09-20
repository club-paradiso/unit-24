from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from radiocorpus.models.common import StrictModel, utcnow


class StageRun(StrictModel):
    run_id: str
    stage: str
    input_fingerprint: str
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    status: str = "running"  # running | completed | failed | partial
    stats: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
