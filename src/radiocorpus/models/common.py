"""Shared enumerations and base types.

Every enumeration carries an explicit UNKNOWN member where absence of knowledge is a
legitimate state. UNKNOWN is never a default that gets silently "upgraded".
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


def utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class AgencyType(StrEnum):
    MUNICIPAL_POLICE = "municipal_police"
    COUNTY_POLICE = "county_police"
    METROPOLITAN_POLICE = "metropolitan_police"  # consolidated city-county police (e.g. metro PDs)
    SHERIFF = "sheriff"
    PRIMARY_STATE_POLICE = "primary_state_police"
    HIGHWAY_PATROL = "highway_patrol"
    STATE_INVESTIGATIVE = "state_investigative"
    UNIVERSITY_POLICE = "university_police"
    TRANSIT_POLICE = "transit_police"
    AIRPORT_POLICE = "airport_police"
    PORT_AUTHORITY_POLICE = "port_authority_police"
    TRIBAL_POLICE = "tribal_police"
    PARK_CONSERVATION_POLICE = "park_conservation_police"
    CAPITOL_POLICE = "capitol_police"
    SCHOOL_DISTRICT_POLICE = "school_district_police"
    HOSPITAL_POLICE = "hospital_police"
    HOUSING_POLICE = "housing_police"
    CONSTABLE = "constable"
    MARSHAL = "marshal"
    CONSOLIDATED_PUBLIC_SAFETY = "consolidated_public_safety"
    SPECIAL_JURISDICTION_POLICE = "special_jurisdiction_police"
    TASK_FORCE_OR_REPORTING_UNIT = "task_force_or_reporting_unit"  # UCR reporting entity, not an agency
    FEDERAL = "federal"  # out of scope; retained for registry completeness
    OTHER = "other"
    UNKNOWN = "unknown"


class ActiveStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class ResearchStatus(StrEnum):
    REGISTRY_ONLY = "registry_only"  # exists in a registry; nothing researched
    SEED_UNCONFIRMED = "seed_unconfirmed"  # curated seed, existence not yet confirmed by discovery
    DISCOVERY_STARTED = "discovery_started"
    DOMAIN_DISCOVERED = "domain_discovered"
    DOCUMENTS_DISCOVERED = "documents_discovered"
    DOCUMENTS_ACQUIRED = "documents_acquired"
    FACTS_EXTRACTED = "facts_extracted"
    NO_PUBLIC_SOURCE = "no_public_source"  # discovery completed; nothing public found
    BLOCKED = "blocked"  # a required operation could not run (e.g. egress)
    UNKNOWN = "unknown"


class SourceType(StrEnum):
    AGENCY_POLICY_MANUAL = "agency_policy_manual"  # general order / SOP / policy manual
    DISPATCH_CENTER_DOCUMENT = "dispatch_center_document"
    GOVERNMENT_DOCUMENT = "government_document"  # city/county/state, not agency-specific policy
    TRAINING_ACCREDITATION = "training_accreditation"
    OTHER_GOVERNMENT_RECORD = "other_government_record"
    STANDARDS_BODY = "standards_body"  # APCO, NIMS/FEMA, NPSTC
    REGISTRY_DATASET = "registry_dataset"
    SEARCH_ENGINE_RESULT = "search_engine_result"  # discovery lead, never authoritative
    SECONDARY_PUBLICATION = "secondary_publication"  # news, academic
    ENTHUSIAST_OR_CROWDSOURCED = "enthusiast_or_crowdsourced"  # scanner sites, wikis, forums
    SOCIAL_MEDIA = "social_media"
    FIXTURE = "fixture"  # synthetic test document
    UNKNOWN = "unknown"


class SourceQuality(StrEnum):
    OFFICIAL_CURRENT = "OFFICIAL_CURRENT"
    OFFICIAL_HISTORICAL = "OFFICIAL_HISTORICAL"
    OFFICIAL_PARTIAL = "OFFICIAL_PARTIAL"
    SECONDARY_CORROBORATED = "SECONDARY_CORROBORATED"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"
    NO_PUBLIC_SOURCE = "NO_PUBLIC_SOURCE"


class Currentness(StrEnum):
    CONFIRMED = "OFFICIAL_CURRENT_CONFIRMED"
    PRESUMED = "OFFICIAL_CURRENT_PRESUMED"
    UNDATED = "OFFICIAL_UNDATED"
    HISTORICAL = "OFFICIAL_HISTORICAL"
    SUPERSEDED = "OFFICIAL_SUPERSEDED"
    UNKNOWN = "CURRENTNESS_UNKNOWN"


class TemporalStatus(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    UNCERTAIN = "uncertain"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"  # official source, deterministic or reviewed extraction, validated
    CORROBORATED = "corroborated"  # >=2 independent sources agree, none official-current
    UNVERIFIED = "unverified"  # candidate; not usable for training
    REJECTED = "rejected"  # failed validation (kept for audit)


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    AUTO_ACCEPTED = "auto_accepted"  # deterministic extraction + validation passed
    NEEDS_REVIEW = "needs_review"
    HUMAN_ACCEPTED = "human_accepted"
    HUMAN_REJECTED = "human_rejected"


class ExtractionMethod(StrEnum):
    DETERMINISTIC_PARSER = "deterministic_parser"
    MODEL = "model"
    HUMAN = "human"
    REGISTRY_IMPORT = "registry_import"


class FactType(StrEnum):
    CODE_MEANING = "code_meaning"
    PHONETIC_LETTER = "phonetic_letter"
    PHONETIC_SYSTEM = "phonetic_system"
    CALLSIGN_CONVENTION = "callsign_convention"
    PROCEDURE_RULE = "procedure_rule"
    ORDERED_STRUCTURE = "ordered_structure"
    INTEROP_RULE = "interop_rule"
    PROTOCOL_MODE = "protocol_mode"


class EligibilityState(StrEnum):
    PLAYABLE_VERIFIED = "PLAYABLE_VERIFIED"
    PLAYABLE_WITH_LIMITATIONS = "PLAYABLE_WITH_LIMITATIONS"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    HISTORICAL_ONLY = "HISTORICAL_ONLY"
    CONFLICT_REQUIRES_REVIEW = "CONFLICT_REQUIRES_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ConflictKind(StrEnum):
    OFFICIAL_VS_OFFICIAL = "official_vs_official"
    CURRENT_VS_OBSOLETE = "current_vs_obsolete"
    AGENCY_VS_DISPATCH = "agency_vs_dispatch"
    STATE_VS_MUNICIPAL = "state_vs_municipal"
    SECONDARY_VS_OFFICIAL = "secondary_vs_official"
    SECONDARY_VS_SECONDARY = "secondary_vs_secondary"
    UNDATED_MANUAL = "undated_manual"
    OTHER = "other"


class ConflictResolution(StrEnum):
    UNRESOLVED = "unresolved"
    RESOLVED_TEMPORAL = "resolved_temporal"  # newer dated official source supersedes older
    RESOLVED_JURISDICTIONAL = "resolved_jurisdictional"  # agency's own doc beats parent/dispatch
    RESOLVED_QUALITY = "resolved_quality"  # official beats secondary
    RESOLVED_HUMAN = "resolved_human"


class AcquisitionStatus(StrEnum):
    PENDING = "pending"
    FETCHED = "fetched"
    BLOCKED_EGRESS = "blocked_egress"
    ROBOTS_DISALLOWED = "robots_disallowed"
    HTTP_ERROR = "http_error"
    NETWORK_ERROR = "network_error"
    SKIPPED_NOT_CANDIDATE = "skipped_not_candidate"
    UNSUPPORTED_CONTENT = "unsupported_content"


class LeadClass(StrEnum):
    OFFICIAL_HOMEPAGE_CANDIDATE = "official_homepage_candidate"
    OFFICIAL_RADIO_POLICY_CANDIDATE = "official_radio_policy_candidate"
    OFFICIAL_DOCUMENT_CANDIDATE = "official_document_candidate"
    STANDARDS_BODY_DOCUMENT = "standards_body_document"
    SECONDARY_LEAD = "secondary_lead"
    ENTHUSIAST_LEAD = "enthusiast_lead"
    UNRELATED = "unrelated"


class LinkStatus(StrEnum):
    CONFIRMED = "confirmed"  # deterministic exact match or human confirmation
    PROPOSED = "proposed"  # heuristic match; needs review
    AMBIGUOUS = "ambiguous"  # multiple plausible targets; preserved, not merged
    REJECTED = "rejected"


US_STATES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
}
US_TERRITORIES = {"PR", "GU", "VI", "AS", "MP", "CZ"}
FIXTURE_STATE = "ZZ"
