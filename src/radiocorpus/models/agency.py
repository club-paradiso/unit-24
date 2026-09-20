"""Canonical agency entity model and registry linkage."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from radiocorpus.models.common import (
    FIXTURE_STATE,
    US_STATES,
    US_TERRITORIES,
    ActiveStatus,
    AgencyType,
    LinkStatus,
    ResearchStatus,
    StrictModel,
    utcnow,
)


class RegistryRecord(StrictModel):
    """A raw row from an external registry, stored verbatim (payload) for audit."""

    registry: str  # e.g. FBI_CDE_FRONTEND_2018, CSLLEA_2018, CURATED_CANARY
    external_id: str  # ORI, ICPSR id, canary_id ...
    name: str | None
    state: str | None
    agency_type_hint: str | None = None
    county: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    registry_snapshot_date: date | None = None
    ingested_at: datetime = Field(default_factory=utcnow)


class Agency(StrictModel):
    agency_id: str
    canonical_name: str
    alternate_names: list[str] = Field(default_factory=list)
    agency_type: AgencyType = AgencyType.UNKNOWN
    country: str = "US"
    state: str | None = None
    county: str | None = None
    municipality: str | None = None
    jurisdiction_description: str | None = None
    parent_agency: str | None = None  # agency_id of parent, when documented
    dispatch_provider: str | None = None  # free text or agency_id; UNKNOWN when None
    official_website: str | None = None  # None == UNKNOWN; set only from evidence
    official_contact_page: str | None = None
    source_registry_ids: dict[str, list[str]] = Field(default_factory=dict)  # registry -> [external ids]
    status: ActiveStatus = ActiveStatus.UNKNOWN
    valid_from: date | None = None
    valid_to: date | None = None
    first_seen: datetime = Field(default_factory=utcnow)
    last_verified: datetime | None = None
    research_status: ResearchStatus = ResearchStatus.UNKNOWN
    is_fixture: bool = False
    notes: str | None = None

    @field_validator("state")
    @classmethod
    def _state(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.upper()
        if v not in US_STATES | US_TERRITORIES | {FIXTURE_STATE}:
            raise ValueError(f"unknown state code {v!r}")
        return v

    @model_validator(mode="after")
    def _fixture_state_guard(self) -> Agency:
        if self.state == FIXTURE_STATE and not self.is_fixture:
            raise ValueError("state ZZ is reserved for fixtures")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to precedes valid_from")
        return self

    def registry_ids(self) -> list[tuple[str, str]]:
        return [(r, i) for r, ids in self.source_registry_ids.items() for i in ids]


class AgencyLink(StrictModel):
    """Proposed or confirmed relation between a canonical agency and a registry record.

    Ambiguous matches are stored, never merged. link_kind distinguishes "this record IS the
    agency" from "this record is a reporting sub-unit of the agency" (e.g. per-county ORIs).
    """

    link_id: str
    agency_id: str
    registry: str
    external_id: str
    link_kind: str  # identity | subunit | related
    status: LinkStatus
    basis: str  # human-readable justification (rule name + evidence)
    score: float | None = None
    competing_agency_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
