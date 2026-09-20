from __future__ import annotations

from datetime import datetime

from pydantic import Field

from radiocorpus.models.common import ConflictKind, ConflictResolution, StrictModel, utcnow


class Conflict(StrictModel):
    conflict_id: str
    agency_id: str
    fact_type: str
    key: str
    fact_ids: list[str]  # all participating facts; none are deleted
    source_ids: list[str]
    kind: ConflictKind
    resolution: ConflictResolution = ConflictResolution.UNRESOLVED
    preferred_fact_id: str | None = None  # only when resolved; other facts remain stored
    rationale: str
    detected_at: datetime = Field(default_factory=utcnow)
    run_id: str | None = None
