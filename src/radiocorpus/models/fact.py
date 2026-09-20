"""Radio-protocol knowledge model: normalized, provenance-bearing facts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from radiocorpus.models.common import (
    ExtractionMethod,
    FactType,
    ReviewStatus,
    StrictModel,
    TemporalStatus,
    VerificationStatus,
    utcnow,
)

MAX_EXCERPT_CHARS = 400  # minimal necessary excerpt; never a document mirror


class CodeMeaning(StrictModel):
    kind: Literal["code_meaning"] = "code_meaning"
    code_system: str  # TEN_CODE | ELEVEN_CODE | SIGNAL | STATUS | DISPOSITION | PENAL_SHORTHAND | OTHER
    code: str  # normalized, e.g. "10-4", "SIGNAL 7", "CODE 3"
    meaning: str
    usage_note: str | None = None


class PhoneticLetter(StrictModel):
    kind: Literal["phonetic_letter"] = "phonetic_letter"
    letter: str
    word: str
    system: str  # NATO | APCO_1941 | LAPD_STYLE | LOCAL | OTHER | UNKNOWN
    context: str | None = None  # e.g. "plates only", "unit designators"

    @field_validator("letter")
    @classmethod
    def _one_letter(cls, v: str) -> str:
        v = v.upper()
        if len(v) != 1 or not v.isalpha():
            raise ValueError("letter must be a single A-Z character")
        return v


class PhoneticSystemAssertion(StrictModel):
    kind: Literal["phonetic_system"] = "phonetic_system"
    system: str
    scope: str | None = None


class CallsignConvention(StrictModel):
    kind: Literal["callsign_convention"] = "callsign_convention"
    element: str  # unit | beat | rank | function | division | precinct
    pattern: str
    examples: list[str] = Field(default_factory=list)
    description: str | None = None


class ProcedureRule(StrictModel):
    kind: Literal["procedure_rule"] = "procedure_rule"
    procedure: str  # acknowledgement | radio_check | repeat_request | correction | readback | emergency_traffic |
    # priority_traffic | clearing_call | traffic_stop | warrant_person_check | vehicle_plate | location_address | numeric
    rule_text: str
    prescribed_phrases: list[str] = Field(default_factory=list)


class OrderedStructure(StrictModel):
    kind: Literal["ordered_structure"] = "ordered_structure"
    structure: str  # vehicle_description | person_description | plate_readback | other
    ordered_fields: list[str]
    mnemonic: str | None = None


class InteropRule(StrictModel):
    kind: Literal["interop_rule"] = "interop_rule"
    rule_kind: str  # plain_language_required | mutual_aid | nims_ics | code_use_restriction | other
    scope: str | None = None
    rule_text: str


class ProtocolModeAssertion(StrictModel):
    kind: Literal["protocol_mode"] = "protocol_mode"
    mode: str  # ten_codes | plain_language | mixed | eleven_codes | signals | other
    scope: str | None = None
    statement: str


FactValue = Annotated[
    CodeMeaning
    | PhoneticLetter
    | PhoneticSystemAssertion
    | CallsignConvention
    | ProcedureRule
    | OrderedStructure
    | InteropRule
    | ProtocolModeAssertion,
    Field(discriminator="kind"),
]

_KIND_TO_TYPE = {
    "code_meaning": FactType.CODE_MEANING,
    "phonetic_letter": FactType.PHONETIC_LETTER,
    "phonetic_system": FactType.PHONETIC_SYSTEM,
    "callsign_convention": FactType.CALLSIGN_CONVENTION,
    "procedure_rule": FactType.PROCEDURE_RULE,
    "ordered_structure": FactType.ORDERED_STRUCTURE,
    "interop_rule": FactType.INTEROP_RULE,
    "protocol_mode": FactType.PROTOCOL_MODE,
}


class ProtocolFact(StrictModel):
    fact_id: str
    agency_id: str
    fact_type: FactType
    key: str  # normalized lookup key within (agency, fact_type): e.g. "10-4", "letter:A", "proc:readback"
    value: FactValue
    raw_value: str | None = None  # verbatim as it appeared (minimal)
    source_id: str
    locator: str  # page/section pointer: "p.12" | "section 4.3" | "html:table#codes row 7"
    excerpt: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    temporal_status: TemporalStatus = TemporalStatus.UNCERTAIN
    supersedes: str | None = None  # fact_id
    superseded_by: str | None = None  # fact_id
    confidence: float = Field(ge=0.0, le=1.0)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    extraction_method: ExtractionMethod
    extraction_model: str | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    run_id: str | None = None

    @model_validator(mode="after")
    def _invariants(self) -> ProtocolFact:
        if _KIND_TO_TYPE[self.value.kind] != self.fact_type:
            raise ValueError(f"value kind {self.value.kind} does not match fact_type {self.fact_type}")
        if not self.source_id:
            raise ValueError("a fact without a source_id is not a fact")
        if not self.locator:
            raise ValueError("locator is required")
        if self.excerpt and len(self.excerpt) > MAX_EXCERPT_CHARS:
            raise ValueError(f"excerpt exceeds {MAX_EXCERPT_CHARS} chars; store minimal excerpts only")
        if self.extraction_method == ExtractionMethod.MODEL and not self.extraction_model:
            raise ValueError("model extraction must record extraction_model")
        if (
            self.extraction_method == ExtractionMethod.MODEL
            and self.verification_status == VerificationStatus.VERIFIED
            and self.review_status
            not in {
                ReviewStatus.HUMAN_ACCEPTED,
            }
        ):
            raise ValueError("model-extracted facts can only be VERIFIED after human acceptance")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to precedes effective_from")
        return self

    def value_fingerprint(self) -> str:
        """Canonical string used to compare two facts' meaning for conflict detection."""
        v = self.value
        if isinstance(v, CodeMeaning):
            return _norm(v.meaning)
        if isinstance(v, PhoneticLetter):
            return _norm(v.word)
        if isinstance(v, PhoneticSystemAssertion):
            return _norm(v.system)
        if isinstance(v, CallsignConvention):
            return _norm(v.pattern)
        if isinstance(v, ProcedureRule):
            return _norm(" | ".join(v.prescribed_phrases) if v.prescribed_phrases else v.rule_text)
        if isinstance(v, OrderedStructure):
            return _norm(">".join(v.ordered_fields))
        if isinstance(v, InteropRule):
            return _norm(v.rule_text)
        if isinstance(v, ProtocolModeAssertion):
            return _norm(v.mode)
        raise TypeError(type(v))


def _norm(s: str) -> str:
    import re

    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s
