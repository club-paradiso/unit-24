"""Independent adjudication of real-document candidates.

The parser must not define its own ground truth. This module is the instrument that keeps
that separation: it turns candidates into a reviewable worksheet, holds one reviewer verdict
per claim a candidate makes, and refuses to compute a metric over claims nobody has judged.

Why a new instrument. The previous review (``data/audit/fact_audit.jsonl``) recorded six
judgements per candidate: meaning support, normalisation, agency attribution, locator,
currentness and learner safety. It found 61/116 meanings supported but only 24/116 complete
facts, and **0/27 procedures with correct applicability scope** — yet it had no field for the
parts a procedure is made of. "Scope is wrong" was recorded without recording *which* part was
wrong, so the finding could not be acted on. A procedure rule is only a fact when its actor,
medium, communication action, governed object, condition, exception and section scope are each
supported by the source; each of those is now judged separately.

Three rules keep this honest:

* **UNADJUDICATED is not a pass.** It is the default for every field, and a metric whose
  population contains an unadjudicated field is reported as ``null`` with the count that
  blocked it. A blank is never read as agreement.
* **A complete fact requires every field.** Meaning support is the weakest claim a candidate
  makes and the easiest to satisfy; it is reported separately from the complete fact precisely
  because the gap between them is where the previous audit found the real damage.
* **Recall needs its own evidence.** Candidates cannot show what a document contains that the
  parser missed. Recall is computed only against a reviewer-supplied inventory of facts the
  document actually holds, and is ``null`` with a reason otherwise.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ADJUDICATION_SCHEMA_VERSION = "adjudication-1"


class Verdict:
    """One reviewer judgement about one claim a candidate makes."""

    SUPPORTED = "SUPPORTED"           # the source says this
    WRONG = "WRONG"                   # the source says something else
    MISSING = "MISSING"               # the candidate does not carry this claim at all
    NOT_APPLICABLE = "NOT_APPLICABLE"  # this claim is meaningless for this family
    UNADJUDICATED = "UNADJUDICATED"   # nobody has looked

    ALL = (SUPPORTED, WRONG, MISSING, NOT_APPLICABLE, UNADJUDICATED)
    #: Verdicts that mean a human (or documented reviewer) has actually decided.
    DECIDED = (SUPPORTED, WRONG, MISSING, NOT_APPLICABLE)


class Currentness:
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    UNKNOWN = "UNKNOWN"
    UNADJUDICATED = "UNADJUDICATED"

    ALL = (CURRENT, HISTORICAL, UNKNOWN, UNADJUDICATED)
    DECIDED = (CURRENT, HISTORICAL, UNKNOWN)


class StructuralFailure:
    """Why a candidate failed, at the granularity the layout layer can act on.

    Aggregating these into one error rate hides which part of the stack is wrong; a column
    bleed and a semantic misclassification need different fixes.
    """

    ADJACENT_COLUMN_BLEED = "ADJACENT_COLUMN_BLEED"
    LOST_WRAPPED_CONTINUATION = "LOST_WRAPPED_CONTINUATION"
    WRONG_READING_ORDER = "WRONG_READING_ORDER"
    HEADING_MISCLASSIFICATION = "HEADING_MISCLASSIFICATION"
    HEADER_FOOTER_CONTAMINATION = "HEADER_FOOTER_CONTAMINATION"
    FALSE_TABLE_INFERENCE = "FALSE_TABLE_INFERENCE"
    MISSED_TABLE_STRUCTURE = "MISSED_TABLE_STRUCTURE"
    WRONG_SECTION_ATTACHMENT = "WRONG_SECTION_ATTACHMENT"
    INCORRECT_CONDITION_EXCEPTION_SCOPE = "INCORRECT_CONDITION_EXCEPTION_SCOPE"
    SEMANTIC_MISCLASSIFICATION = "SEMANTIC_MISCLASSIFICATION"
    DATE_OR_REVISION_MISREAD = "DATE_OR_REVISION_MISREAD"
    OTHER = "OTHER"
    NOT_A_FAILURE = "NOT_A_FAILURE"
    UNADJUDICATED = "UNADJUDICATED"

    ALL = (
        ADJACENT_COLUMN_BLEED, LOST_WRAPPED_CONTINUATION, WRONG_READING_ORDER,
        HEADING_MISCLASSIFICATION, HEADER_FOOTER_CONTAMINATION, FALSE_TABLE_INFERENCE,
        MISSED_TABLE_STRUCTURE, WRONG_SECTION_ATTACHMENT, INCORRECT_CONDITION_EXCEPTION_SCOPE,
        SEMANTIC_MISCLASSIFICATION, DATE_OR_REVISION_MISREAD, OTHER, NOT_A_FAILURE, UNADJUDICATED,
    )


#: Fields every family must satisfy before a candidate is a complete fact.
COMMON_FIELDS = (
    "meaning_supported",
    "agency_correct",
    "issuing_authority_correct",
    "region_correct",
    "learner_safe_in_principle",
)
#: Additional fields per family. A procedure carries far more claims than a code does, which
#: is why its complete-fact rate is so much lower than its meaning-support rate.
FAMILY_FIELDS = {
    "code_meaning": ("code_exact",),
    "phonetic_letter": ("code_exact",),
    "procedure_rule": (
        "procedure_actor",
        "communication_medium",
        "communication_action",
        "governed_object",
        "condition_correct",
        "exception_correct",
        "section_scope_correct",
        "context_complete",
    ),
}
#: The claims that together are "applicability scope" — the set the previous audit found
#: wrong on every single procedure without recording which part failed.
SCOPE_FIELDS = ("section_scope_correct", "condition_correct", "exception_correct")
#: Claims the extraction layer is not responsible for. The issuing authority is a property of
#: the source ledger, and learner safety is the downstream human gate. Folding them into one
#: completeness number makes a parser look broken for something it was never asked to do, so
#: completeness is reported twice: what the parser owes, and what a learner-ready fact needs.
DOWNSTREAM_FIELDS = ("issuing_authority_correct", "learner_safe_in_principle")


@dataclass
class AdjudicationRecord:
    """One candidate, every claim it makes, and the reviewer's verdict on each."""

    adjudication_id: str
    document_key: str
    document_sha256: str | None
    family: str
    candidate_id: str
    locator: str
    excerpt: str
    parser_value: dict = field(default_factory=dict)
    parser_version: str = ""
    structural_reason: str = ""

    # --- the claims, one verdict each -------------------------------------------------
    meaning_supported: str = Verdict.UNADJUDICATED
    code_exact: str = Verdict.UNADJUDICATED
    agency_correct: str = Verdict.UNADJUDICATED
    issuing_authority_correct: str = Verdict.UNADJUDICATED
    region_correct: str = Verdict.UNADJUDICATED
    currentness: str = Currentness.UNADJUDICATED
    procedure_actor: str = Verdict.UNADJUDICATED
    communication_medium: str = Verdict.UNADJUDICATED
    communication_action: str = Verdict.UNADJUDICATED
    governed_object: str = Verdict.UNADJUDICATED
    condition_correct: str = Verdict.UNADJUDICATED
    exception_correct: str = Verdict.UNADJUDICATED
    section_scope_correct: str = Verdict.UNADJUDICATED
    context_complete: str = Verdict.UNADJUDICATED
    learner_safe_in_principle: str = Verdict.UNADJUDICATED
    structural_failure: str = StructuralFailure.UNADJUDICATED

    # --- who decided, and on what evidence --------------------------------------------
    reviewer: str = ""
    reviewer_is_human: bool = False
    review_method: str = ""
    reviewed_at: str = ""
    inspection: str = ""
    notes: str = ""
    seeded_from: str = ""
    #: Claims decided without a reviewer, because the candidate never made them. Recorded so a
    #: mechanical decision can never be mistaken for a judgement about a document.
    mechanically_decided: tuple[str, ...] = ()
    mechanical_rule: str = ""
    schema_version: str = ADJUDICATION_SCHEMA_VERSION

    # ----------------------------------------------------------------------------------
    def required_fields(self) -> tuple[str, ...]:
        return COMMON_FIELDS + FAMILY_FIELDS.get(self.family, ())

    def extraction_fields(self) -> tuple[str, ...]:
        """The claims the parser is answerable for."""
        return tuple(f for f in self.required_fields() if f not in DOWNSTREAM_FIELDS)

    def unadjudicated_fields(self) -> list[str]:
        out = [f for f in self.required_fields() if getattr(self, f) == Verdict.UNADJUDICATED]
        if self.currentness == Currentness.UNADJUDICATED:
            out.append("currentness")
        return out

    def is_adjudicated(self) -> bool:
        return not self.unadjudicated_fields()

    def reviewer_decided_fields(self) -> list[str]:
        """Claims a reviewer judged, as opposed to ones decided by their own absence."""
        mechanical = set(self.mechanically_decided)
        return [
            f for f in self.required_fields()
            if getattr(self, f) != Verdict.UNADJUDICATED and f not in mechanical
        ]

    def blocking_fields(self) -> list[str]:
        """Claims that stop this candidate being a complete fact."""
        if not self.is_adjudicated():
            return []
        return [
            f for f in self.required_fields()
            if getattr(self, f) not in (Verdict.SUPPORTED, Verdict.NOT_APPLICABLE)
        ]

    def meaning_is_supported(self) -> bool | None:
        if self.meaning_supported == Verdict.UNADJUDICATED:
            return None
        return self.meaning_supported == Verdict.SUPPORTED

    def is_complete_fact(self) -> bool | None:
        """A complete fact supports every claim it makes. Unknown while anything is unjudged."""
        if not self.is_adjudicated():
            return None
        return all(
            getattr(self, f) in (Verdict.SUPPORTED, Verdict.NOT_APPLICABLE)
            for f in self.required_fields()
        )

    def is_extraction_complete(self) -> bool | None:
        """Every claim the parser owes, supported. Says nothing about whether it may be used."""
        fields = self.extraction_fields()
        if any(getattr(self, f) == Verdict.UNADJUDICATED for f in fields):
            return None
        return all(getattr(self, f) in (Verdict.SUPPORTED, Verdict.NOT_APPLICABLE) for f in fields)

    def scope_is_correct(self) -> bool | None:
        if self.family != "procedure_rule":
            return None
        if any(getattr(self, f) == Verdict.UNADJUDICATED for f in SCOPE_FIELDS):
            return None
        return all(getattr(self, f) in (Verdict.SUPPORTED, Verdict.NOT_APPLICABLE) for f in SCOPE_FIELDS)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MissedFact:
    """A fact the reviewer found in the document that no candidate carried.

    Recall cannot come from the candidates: they cannot show what is absent. Without this
    inventory the denominator does not exist, and the scorer says so rather than inventing it.
    """

    document_key: str
    family: str
    expected_key: str
    expected_value: str
    locator: str
    reviewer: str
    reviewer_is_human: bool = False
    reviewed_at: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- worksheet construction


def worksheet_from_candidates(rows: list[dict], *, hashes: dict[str, str] | None = None) -> list[AdjudicationRecord]:
    """Turn parser candidates into blank adjudication records.

    Every verdict starts UNADJUDICATED. Nothing about the parser's own output is allowed to
    pre-fill a judgement about whether the source supports it.
    """
    hashes = hashes or {}
    out: list[AdjudicationRecord] = []
    for i, row in enumerate(rows):
        family = row.get("family", "")
        if family == "code_meaning":
            value = {"code": row.get("code"), "meaning": row.get("meaning")}
            cid = f"{row.get('code')}"
        elif family == "phonetic_letter":
            value = {"letter": row.get("letter"), "word": row.get("word")}
            cid = f"{row.get('letter')}"
        else:
            parts = row.get("decomposition") or {}
            value = {
                "procedure": row.get("procedure"),
                "medium": row.get("medium"),
                "rule_text": row.get("rule_text"),
                "section_heading": row.get("section_heading"),
                "has_condition": row.get("has_condition"),
                "has_exception": row.get("has_exception"),
                "parser_context_complete": row.get("context_complete"),
                # Present and null when the sentence states no actor: the candidate makes no
                # such claim, and the worksheet must be able to tell that apart from nobody
                # having looked.
                "actor": (parts.get("actor") or {}).get("text"),
                "communication_action": (parts.get("communication_action") or {}).get("text"),
                "governed_object": (parts.get("governed_object") or {}).get("text"),
            }
            cid = f"{row.get('procedure')}"
        doc = row.get("document", "")
        record = AdjudicationRecord(
            adjudication_id=f"adj_{doc}_{family}_{i:04d}",
            document_key=doc,
            document_sha256=hashes.get(doc),
            family=family,
            candidate_id=str(cid),
            locator=row.get("locator", ""),
            excerpt=(row.get("excerpt") or row.get("rule_text") or "")[:500],
            parser_value=value,
            structural_reason=row.get("structural_reason", ""),
        )
        mark_inapplicable(record)
        out.append(record)
    return out


def mark_inapplicable(record: AdjudicationRecord) -> AdjudicationRecord:
    """Mark every claim this family cannot make as NOT_APPLICABLE.

    Leaving them blank would be indistinguishable from "nobody looked", and the scorer treats
    those two very differently: one is a fact about the family, the other is missing work.
    """
    required = set(record.required_fields())
    for group in FAMILY_FIELDS.values():
        for name in group:
            if name not in required:
                setattr(record, name, Verdict.NOT_APPLICABLE)
    return record


# ---------------------------------------------------------------- claims a candidate never made

#: Where a candidate would carry each claim, if it carried it at all. A claim is *absent* when
#: none of its carrier keys appears in the candidate's recorded value.
#:
#: Absence is a fact about the candidate, not about the document, so it can be decided without
#: the source. That distinction matters: everything else in this module needs the document, and
#: conflating the two would let a mechanical pass masquerade as a review.
CLAIM_CARRIERS: dict[str, tuple[str, ...]] = {
    "issuing_authority_correct": ("issuing_authority", "issuer"),
    "procedure_actor": ("actor", "procedure_actor"),
    "communication_medium": ("medium",),
    "communication_action": ("action", "communication_action"),
    "governed_object": ("governed_object", "object"),
    "condition_correct": ("has_condition", "condition"),
    "exception_correct": ("has_exception", "exception"),
    "section_scope_correct": ("section_heading", "section_path", "applicability_scope"),
    "context_complete": ("context_complete", "parser_context_complete"),
}
ABSENCE_RULE = "claim_absent_from_candidate:no_carrier_key_in_parser_value"


def claim_is_carried(record: AdjudicationRecord, claim: str) -> bool:
    """Whether the candidate makes this claim at all.

    A key present but false still carries a claim — ``has_condition: false`` asserts that no
    condition governs the rule, which a reviewer can agree or disagree with. A key that is
    absent, or present and null, carries nothing.
    """
    for key in CLAIM_CARRIERS.get(claim, ()):
        if key in record.parser_value and record.parser_value[key] is not None:
            return True
    return False


def mark_absent_claims(record: AdjudicationRecord) -> list[str]:
    """Decide the claims this candidate never made, and only those.

    Returns the field names decided. An existing verdict is never overwritten: a reviewer's
    judgement outranks a mechanical one, always.
    """
    decided: list[str] = []
    for claim in record.required_fields():
        if getattr(record, claim) != Verdict.UNADJUDICATED:
            continue
        if claim in CLAIM_CARRIERS and not claim_is_carried(record, claim):
            setattr(record, claim, Verdict.MISSING)
            decided.append(claim)
    if decided:
        record.mechanically_decided = tuple(sorted(set(record.mechanically_decided) | set(decided)))
        record.mechanical_rule = ABSENCE_RULE
    return decided


# ---------------------------------------------------------------- seeding from the prior review

#: The previous review's flags, mapped onto the claims they actually judged. Six of the
#: fifteen. Everything absent from this table stays UNADJUDICATED, because the old instrument
#: never asked the question and a verdict cannot be invented from one that was never given.
_SEEDED_FROM_AUDIT = {
    "meaning_supported": "exact_meaning_supported",
    "agency_correct": "agency_attribution_correct",
    "region_correct": "locator_correct",
    "learner_safe_in_principle": "safe_expected_answer",
}
#: Deliberately NOT seeded, and why:
#:   issuing_authority_correct - the old ``source_authoritative`` judges the *source*, not who
#:                               issued the document; conflating host and issuer is the error
#:                               this field exists to catch.
#:   procedure_actor, communication_medium, communication_action, governed_object,
#:   condition_correct, exception_correct, context_complete
#:                             - never asked. This is why "0/27 scope correct" could not be
#:                               acted on: the instrument recorded the failure, not its part.
UNSEEDABLE_FIELDS = (
    "issuing_authority_correct",
    "procedure_actor",
    "communication_medium",
    "communication_action",
    "governed_object",
    "condition_correct",
    "exception_correct",
    "context_complete",
)

_FAILURE_ALIASES = {
    "LAYOUT_COLUMN_BLEED": StructuralFailure.ADJACENT_COLUMN_BLEED,
    "LAYOUT_CONTINUATION_LOST": StructuralFailure.LOST_WRAPPED_CONTINUATION,
    "DATE_OR_REVISION_MISREAD": StructuralFailure.DATE_OR_REVISION_MISREAD,
    "HEADING_MISREAD": StructuralFailure.HEADING_MISCLASSIFICATION,
    "SEMANTIC_MISCLASSIFICATION": StructuralFailure.SEMANTIC_MISCLASSIFICATION,
    "CONTEXT_OMITTED": StructuralFailure.INCORRECT_CONDITION_EXCEPTION_SCOPE,
    "PAGE_FURNITURE": StructuralFailure.HEADER_FOOTER_CONTAMINATION,
    "NOT_A_FAILURE": StructuralFailure.NOT_A_FAILURE,
    "UNCLASSIFIED": StructuralFailure.OTHER,
}


def _verdict(flag: object) -> str:
    if flag is True:
        return Verdict.SUPPORTED
    if flag is False:
        return Verdict.WRONG
    return Verdict.UNADJUDICATED


def seed_from_audit(
    audit_rows: list[dict],
    facts: dict[str, dict],
    *,
    document_keys: dict[str, str],
    hashes: dict[str, str] | None = None,
) -> list[AdjudicationRecord]:
    """Restate the previous review in the richer instrument.

    Nothing is re-judged here and nothing is inferred: a flag the reviewer set becomes the
    corresponding verdict, and a question the reviewer was never asked stays UNADJUDICATED.
    The result quantifies exactly how much of a complete-fact judgement the earlier audit
    could support — which turns out to be six claims out of fifteen.
    """
    from radiocorpus.evaluation.gold import classify_failure

    hashes = hashes or {}
    out: list[AdjudicationRecord] = []
    for a in audit_rows:
        fact = facts.get(a["fact_id"], {})
        family = a["fact_type"]
        doc = document_keys.get(a["source_id"], a["source_id"])
        record = AdjudicationRecord(
            adjudication_id=f"adj_seed_{a['audit_index']:04d}",
            document_key=doc,
            document_sha256=hashes.get(a["source_id"]),
            family=family,
            candidate_id=a.get("key", ""),
            locator=a.get("locator", ""),
            excerpt=(fact.get("excerpt") or "")[:500],
            parser_value=fact.get("value", {}),
            parser_version=str(fact.get("extraction_rule_version") or ""),
            structural_reason=str(fact.get("extraction_rule") or ""),
            reviewer=a.get("reviewer", ""),
            reviewer_is_human=bool(a.get("human_review")),
            review_method=a.get("review_method", ""),
            reviewed_at=a.get("reviewed_at", ""),
            inspection=a.get("inspection", ""),
            notes=a.get("reason", ""),
            seeded_from="data/audit/fact_audit.jsonl",
        )
        mark_inapplicable(record)
        for target, source in _SEEDED_FROM_AUDIT.items():
            if target in record.required_fields():
                setattr(record, target, _verdict(a.get(source)))
        if "code_exact" in record.required_fields():
            record.code_exact = _verdict(a.get("normalized_metadata_correct"))
        if "section_scope_correct" in record.required_fields():
            # The old flag is one coarse verdict covering everything the new instrument splits
            # into section scope, condition and exception. It is carried onto section scope
            # only; the other two stay unadjudicated rather than inheriting a verdict that was
            # never separately given.
            record.section_scope_correct = _verdict(a.get("applicability_scope_correct"))
        current = a.get("source_current")
        record.currentness = Currentness.CURRENT if current is True else (
            Currentness.UNKNOWN if current in ("not_confirmed", None, False) else Currentness.UNADJUDICATED
        )
        supported = bool(a.get("exact_meaning_supported"))
        record.structural_failure = _FAILURE_ALIASES.get(
            classify_failure(a.get("reason") or "", supported=supported), StructuralFailure.OTHER
        )
        out.append(record)
    return out


def seeding_coverage(records: list[AdjudicationRecord]) -> dict:
    """How much of a complete-fact judgement the seeded verdicts can support."""
    per_field: dict[str, dict[str, int]] = {}
    for r in records:
        for name in r.required_fields():
            bucket = per_field.setdefault(name, {"decided": 0, "unadjudicated": 0, "applicable": 0})
            bucket["applicable"] += 1
            if getattr(r, name) == Verdict.UNADJUDICATED:
                bucket["unadjudicated"] += 1
            else:
                bucket["decided"] += 1
    return {
        "records": len(records),
        "fully_adjudicated": sum(1 for r in records if r.is_adjudicated()),
        "per_field": dict(sorted(per_field.items())),
        "never_asked_by_the_previous_instrument": list(UNSEEDABLE_FIELDS),
    }


# ---------------------------------------------------------------- scoring


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _metric(records: list[AdjudicationRecord], predicate, *, field_names: tuple[str, ...]) -> dict:
    """Score one predicate, refusing when any contributing field is unadjudicated."""
    blocked = [
        r for r in records
        if any(getattr(r, f) == Verdict.UNADJUDICATED for f in field_names)
    ]
    judged = [r for r in records if r not in blocked]
    if blocked:
        return {
            "emitted": len(records),
            "adjudicated": len(judged),
            "unadjudicated": len(blocked),
            "tp": None, "fp": None, "precision": None,
            "blocked_reason": f"{len(blocked)} of {len(records)} candidates have an unadjudicated field",
        }
    tp = sum(1 for r in judged if predicate(r))
    return {
        "emitted": len(records),
        "adjudicated": len(judged),
        "unadjudicated": 0,
        "tp": tp,
        "fp": len(judged) - tp,
        "precision": _rate(tp, len(judged)),
    }


def score(
    records: list[AdjudicationRecord],
    missed: list[MissedFact] | None = None,
    *,
    current_parser_versions: dict[str, str] | None = None,
) -> dict:
    """Real-document metrics, per family and per document.

    Nothing here is comparable to a synthetic-corpus figure and the two are never summed.

    ``current_parser_versions`` lets the result say whether these candidates came from the
    parsers in the tree today. A precision measured on an older parser's candidates is a fact
    about that parser, and reading it as a current figure is the specific mistake this block
    exists to prevent.
    """
    missed = missed or []
    families = sorted({r.family for r in records})
    documents = sorted({r.document_key for r in records})

    def block(subset: list[AdjudicationRecord], family: str, document: str | None) -> dict:
        if not subset:
            return {"emitted": 0}
        out: dict = {
            "candidate_meaning": _metric(subset, lambda r: r.meaning_is_supported() is True,
                                         field_names=("meaning_supported",)),
            "extraction_complete": _metric(subset, lambda r: r.is_extraction_complete() is True,
                                           field_names=subset[0].extraction_fields()),
            "complete_fact": _metric(subset, lambda r: r.is_complete_fact() is True,
                                     field_names=subset[0].required_fields()),
        }
        if family == "procedure_rule":
            marked = [r for r in subset if r.parser_value.get("parser_context_complete") is True]
            out["parser_context_complete_subset"] = _metric(
                marked, lambda r: r.meaning_is_supported() is True, field_names=("meaning_supported",)
            ) if marked else {"emitted": 0, "note": "the parser marked no candidate context_complete"}
            out["reviewer_context_complete"] = _metric(
                subset, lambda r: r.context_complete == Verdict.SUPPORTED, field_names=("context_complete",)
            )
            out["complete_scope"] = _metric(
                subset, lambda r: r.scope_is_correct() is True, field_names=SCOPE_FIELDS
            )
        fn = [m for m in missed if m.family == family and (document is None or m.document_key == document)]
        judged = out["candidate_meaning"].get("tp")
        if fn and judged is not None:
            out["recall"] = {
                "tp": judged, "fn": len(fn),
                "recall": _rate(judged, judged + len(fn)),
                "source": "reviewer-supplied missed-fact inventory",
            }
        else:
            out["recall"] = {
                "tp": judged, "fn": None, "recall": None,
                "blocked_reason": "no reviewer-supplied inventory of facts the document contains; "
                                  "candidates cannot evidence what was missed",
            }
        failures: dict[str, int] = {}
        for r in subset:
            if r.meaning_is_supported() is False:
                failures[r.structural_failure] = failures.get(r.structural_failure, 0) + 1
        out["structural_failures"] = dict(sorted(failures.items()))
        # Which claims stop these candidates being complete facts. Without this the
        # complete-fact rate is a number with no cause attached, and a systemic gap - one
        # claim absent from every candidate - reads as if every candidate were wrong.
        blocking: dict[str, int] = {}
        for r in subset:
            for name in r.blocking_fields():
                blocking[name] = blocking.get(name, 0) + 1
        out["blocking_claims"] = dict(sorted(blocking.items(), key=lambda kv: (-kv[1], kv[0])))
        out["blocking_claims_note"] = (
            "Counts overlap: one candidate can be blocked by several claims. A claim blocking "
            "every candidate is a systemic gap, not a per-candidate error."
        )
        return out

    per_family = {f: block([r for r in records if r.family == f], f, None) for f in families}
    per_document = {
        d: {f: block([r for r in records if r.family == f and r.document_key == d], f, d) for f in families}
        for d in documents
    }
    reviewers = sorted({r.reviewer for r in records if r.reviewer})
    seen_versions = sorted({r.parser_version for r in records if r.parser_version})
    provenance: dict[str, object] = {
        "candidate_parser_versions": seen_versions,
        "seeded_from": sorted({r.seeded_from for r in records if r.seeded_from}),
    }
    if current_parser_versions:
        provenance["current_parser_versions"] = dict(sorted(current_parser_versions.items()))
        stale = seen_versions and not set(seen_versions) <= set(current_parser_versions.values())
        provenance["measures_current_parsers"] = not stale
        if stale:
            provenance["warning"] = (
                f"These candidates were emitted by parser version(s) {seen_versions}; the tree now runs "
                f"{sorted(set(current_parser_versions.values()))}. Every figure below is a measurement of "
                "the older parser on real documents, not of the current one."
            )
    reviewer_fields = sum(len(r.reviewer_decided_fields()) for r in records)
    mechanical_fields = sum(len(r.mechanically_decided) for r in records)
    open_fields = sum(len(r.unadjudicated_fields()) for r in records)
    return {
        "schema_version": ADJUDICATION_SCHEMA_VERSION,
        "candidates": len(records),
        "documents": documents,
        "candidate_provenance": provenance,
        "fully_adjudicated": sum(1 for r in records if r.is_adjudicated()),
        "unadjudicated": sum(1 for r in records if not r.is_adjudicated()),
        "claims_decided_by": {
            "reviewer": reviewer_fields,
            "absence_from_the_candidate": mechanical_fields,
            "still_open": open_fields,
            "note": (
                "A claim decided by its own absence was never judged against a document. "
                "'Fully adjudicated' therefore does not mean 'reviewed'."
            ),
        },
        "human_adjudicated_candidates": sum(1 for r in records if r.reviewer_is_human),
        "reviewers": reviewers,
        "any_human_reviewer": any(r.reviewer_is_human for r in records),
        "per_family": per_family,
        "per_document": per_document,
        "note": (
            "Real-document metrics only. Never combine with the synthetic stress corpus: a "
            "figure from generated geometry is not evidence about a published document."
        ),
    }


# ---------------------------------------------------------------- persistence


def write_records(records: list[AdjudicationRecord], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for r in records:
            handle.write(json.dumps(r.to_dict(), sort_keys=True) + "\n")
    return len(records)


def read_records(path: Path) -> list[AdjudicationRecord]:
    out: list[AdjudicationRecord] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                row["mechanically_decided"] = tuple(row.get("mechanically_decided") or ())
                out.append(AdjudicationRecord(**row))
    return out


def read_missed(path: Path) -> list[MissedFact]:
    if not path.exists():
        return []
    out: list[MissedFact] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                out.append(MissedFact(**json.loads(line)))
    return out


__all__ = [
    "ADJUDICATION_SCHEMA_VERSION",
    "COMMON_FIELDS",
    "FAMILY_FIELDS",
    "DOWNSTREAM_FIELDS",
    "SCOPE_FIELDS",
    "AdjudicationRecord",
    "Currentness",
    "MissedFact",
    "StructuralFailure",
    "UNSEEDABLE_FIELDS",
    "Verdict",
    "mark_inapplicable",
    "CLAIM_CARRIERS",
    "claim_is_carried",
    "mark_absent_claims",
    "read_missed",
    "read_records",
    "score",
    "seed_from_audit",
    "seeding_coverage",
    "worksheet_from_candidates",
    "write_records",
]
