"""Evidence objects: sources, document leads, acquired documents."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field, model_validator

from radiocorpus.models.common import (
    AcquisitionStatus,
    LeadClass,
    SourceQuality,
    SourceType,
    StrictModel,
    TemporalStatus,
    utcnow,
)


class DocumentLead(StrictModel):
    """Something discovered (a URL) that MAY be evidence. Never authoritative by itself."""

    lead_id: str
    agency_id: str
    url: str
    host: str
    title: str | None = None
    snippet: str | None = None
    discovered_via: str  # search_engine:<engine> | manual | site_crawl | registry
    query: str | None = None
    rank: int | None = None
    retrieved_at: datetime
    lead_class: LeadClass = LeadClass.UNRELATED
    classification_basis: str | None = None
    host_is_official: bool | None = None  # None == unknown
    acquisition_status: AcquisitionStatus = AcquisitionStatus.PENDING
    acquisition_note: str | None = None
    source_id: str | None = None  # set once acquired
    worker_note: str | None = None


class Source(StrictModel):
    source_id: str
    source_type: SourceType
    title: str | None
    issuing_authority: str | None
    agency_or_jurisdiction: str | None  # agency_id or descriptive jurisdiction
    canonical_url: str
    original_file_url: str | None = None
    retrieved_at: datetime = Field(default_factory=utcnow)
    publication_date: date | None = None
    effective_date: date | None = None
    revision: str | None = None
    page_count: int | None = None
    document_hash: str | None = None  # sha256:<hex> of the acquired bytes; None if never acquired
    local_path: str | None = None  # relative to repo root; None if not stored
    content_type: str | None = None
    source_quality: SourceQuality = SourceQuality.UNVERIFIED
    temporal_status: TemporalStatus = TemporalStatus.UNCERTAIN
    superseded_by: str | None = None  # source_id
    supersedes: str | None = None  # source_id
    is_fixture: bool = False
    notes: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _quality_requires_acquisition(self) -> Source:
        # An OFFICIAL_* quality can only be asserted for a document we actually hold (hashed),
        # otherwise it is a lead. Fixtures follow the same rule.
        if (
            self.source_quality
            in {
                SourceQuality.OFFICIAL_CURRENT,
                SourceQuality.OFFICIAL_HISTORICAL,
                SourceQuality.OFFICIAL_PARTIAL,
            }
            and not self.document_hash
        ):
            raise ValueError("official source quality requires an acquired, hashed document")
        if self.source_type == SourceType.SEARCH_ENGINE_RESULT and self.source_quality != SourceQuality.UNVERIFIED:
            raise ValueError("search-engine results are always UNVERIFIED")
        if self.source_type in {SourceType.ENTHUSIAST_OR_CROWDSOURCED, SourceType.SOCIAL_MEDIA} and self.source_quality in {
            SourceQuality.OFFICIAL_CURRENT,
            SourceQuality.OFFICIAL_HISTORICAL,
            SourceQuality.OFFICIAL_PARTIAL,
        }:
            raise ValueError("crowdsourced/social sources can never be OFFICIAL_*")
        return self

    @property
    def is_official(self) -> bool:
        return self.source_quality in {
            SourceQuality.OFFICIAL_CURRENT,
            SourceQuality.OFFICIAL_HISTORICAL,
            SourceQuality.OFFICIAL_PARTIAL,
        }


class DocumentRecord(StrictModel):
    """The acquired bytes + extracted text for a source. Content-addressed by hash."""

    document_hash: str
    source_id: str
    local_path: str
    text_path: str | None = None
    content_type: str | None
    byte_length: int
    page_count: int | None = None
    acquired_at: datetime = Field(default_factory=utcnow)
    extraction_tool: str | None = None
