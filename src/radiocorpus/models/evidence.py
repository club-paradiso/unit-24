"""Explicit, scoped evidence; relationships alone grant no protocol applicability."""

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from radiocorpus.models.common import FactType, StrictModel


class EvidencePointer(StrictModel):
    evidence_source_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    excerpt: str = Field(min_length=1, max_length=400)
    verification_status: Literal["unverified", "verified"] = "unverified"
    verified_by: str | None = None

    @model_validator(mode="after")
    def reviewer_required(self):
        if self.verification_status == "verified" and not self.verified_by:
            raise ValueError("verified evidence requires reviewer attribution")
        return self


class IdentityEvidence(EvidencePointer):
    target_agency_id: str
    canonical_name: str
    state: str
    host: str
    basis: Literal["official_directory", "agency_page", "government_link"]


class CurrentnessEvidence(EvidencePointer):
    target_source_id: str
    basis: Literal["active_policy_portal", "current_policy_index", "explicit_effective_policy", "revision_metadata", "archive", "supersession"]
    checked_on: date
    recheck_by: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class ProtocolApplicabilityEvidence(EvidencePointer):
    source_agency_or_dispatcher: str
    target_agency: str
    protocol_source_id: str
    scope: list[FactType] = Field(min_length=1)
    fact_keys: list[str] = Field(min_length=1)
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def dates_ordered(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("inverted applicability period")
        return self


class IssuingAuthorityEvidence(EvidencePointer):
    target_source_id: str
    issuing_authority_id: str


class FactReviewEvidence(StrictModel):
    fact_id: str
    source_id: str
    document_hash: str
    value_fingerprint: str
    reviewer_id: str = Field(min_length=1)
    reviewer_kind: Literal["human", "model"]
    reviewed_on: date
    decision: Literal["accepted", "rejected"]
