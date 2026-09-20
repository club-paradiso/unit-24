from __future__ import annotations

from datetime import datetime

from pydantic import Field

from radiocorpus.models.common import EligibilityState, StrictModel, utcnow


class EligibilityDecision(StrictModel):
    subject_kind: str  # fact | agency
    subject_id: str
    state: EligibilityState
    reasons: list[str]
    supporting_source_ids: list[str] = Field(default_factory=list)
    conflict_ids: list[str] = Field(default_factory=list)
    policy_version: str
    decided_at: datetime = Field(default_factory=utcnow)


class TrainingItem(StrictModel):
    """Shape of a future learner-facing exercise. It cannot exist without fact + evidence refs."""

    item_id: str
    agency_id: str
    exercise_kind: str  # readback | code_meaning | phonetic_spell | ...
    prompt: str
    expected_answer: str
    fact_ids: list[str] = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    eligibility: EligibilityState
    limitations: list[str] = Field(default_factory=list)
