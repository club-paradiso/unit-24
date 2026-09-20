"""Gold / correction labels for extraction evaluation.

The labels are **derived mechanically** from the independent review committed in
``data/audit/fact_audit.jsonl``. Nothing here re-judges a document: each derived label is a
restatement of flags that the independent reviewer already recorded, and every record keeps
the original flags plus the derivation rule that produced the label. The original audit file
is never modified.

A derived label is therefore evidence about *the candidate the previous parser emitted*. It
does not automatically transfer to a differently-shaped candidate emitted by a new parser;
where the text changes, re-adjudication is required and the harness says so.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

GOLD_SCHEMA_VERSION = "gold-1"


class Label:
    TRUE_FACT = "TRUE_FACT"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    WRONG_NORMALIZATION = "WRONG_NORMALIZATION"
    WRONG_SCOPE = "WRONG_SCOPE"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class FailureClass:
    LAYOUT_COLUMN_BLEED = "LAYOUT_COLUMN_BLEED"
    LAYOUT_CONTINUATION_LOST = "LAYOUT_CONTINUATION_LOST"
    DATE_OR_REVISION_MISREAD = "DATE_OR_REVISION_MISREAD"
    HEADING_MISREAD = "HEADING_MISREAD"
    SEMANTIC_MISCLASSIFICATION = "SEMANTIC_MISCLASSIFICATION"
    CONTEXT_OMITTED = "CONTEXT_OMITTED"
    PAGE_FURNITURE = "PAGE_FURNITURE"
    NOT_A_FAILURE = "NOT_A_FAILURE"
    UNCLASSIFIED = "UNCLASSIFIED"


_BLEED = re.compile(r"multi-?column bleed|adjacent (?:code|statutory|column)|belongs to adjacent|merged", re.I)
_CONTINUATION = re.compile(r"continuation .*omitted|truncat|qualifier .*(?:omitted|truncated)", re.I)
_DATE = re.compile(r"revision date|issue date|date .*misread", re.I)
_HEADING = re.compile(r"section heading|heading .*misread|section [A-Z]\.", re.I)
_FURNITURE = re.compile(r"page footer|footer ingested|header ingested", re.I)
_CONTEXT = re.compile(r"omits|antecedent|condition needed|next page|following", re.I)
_SEMANTIC = re.compile(
    r"is not (?:radio|a radio)|not a radio|not radio|definition of|workflow|paperwork|greeting|"
    r"misclassified|misread as|dispatch response mode|transfer workflow|equipment request",
    re.I,
)


@dataclass
class GoldRecord:
    gold_id: str
    fact_id: str
    agency_id: str
    source_id: str
    document_key: str
    fact_type: str
    key: str
    locator: str
    expected_value: dict
    excerpt: str
    label: str
    failure_class: str
    rationale: str
    reviewer: str
    review_method: str
    reviewed_at: str
    source_document_hash: str | None
    label_source: str = "derived_from_independent_audit"
    derivation_rule: str = ""
    original_flags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def classify_failure(reason: str, *, supported: bool) -> str:
    if supported:
        return FailureClass.NOT_A_FAILURE
    for pattern, name in (
        (_BLEED, FailureClass.LAYOUT_COLUMN_BLEED),
        (_DATE, FailureClass.DATE_OR_REVISION_MISREAD),
        (_HEADING, FailureClass.HEADING_MISREAD),
        (_FURNITURE, FailureClass.PAGE_FURNITURE),
        (_CONTINUATION, FailureClass.LAYOUT_CONTINUATION_LOST),
        (_SEMANTIC, FailureClass.SEMANTIC_MISCLASSIFICATION),
        (_CONTEXT, FailureClass.CONTEXT_OMITTED),
    ):
        if pattern.search(reason):
            return name
    return FailureClass.UNCLASSIFIED


def derive_label(audit: dict) -> tuple[str, str]:
    """Map the reviewer's flags onto the correction taxonomy. Returns (label, rule)."""
    meaning = bool(audit.get("exact_meaning_supported"))
    normalized = bool(audit.get("normalized_metadata_correct"))
    scope = bool(audit.get("applicability_scope_correct"))
    reason = audit.get("reason") or ""
    if not meaning:
        if _CONTEXT.search(reason) or _CONTINUATION.search(reason):
            return Label.INSUFFICIENT_CONTEXT, "meaning_unsupported+context_reason"
        return Label.FALSE_POSITIVE, "meaning_unsupported"
    if meaning and normalized and scope:
        return Label.TRUE_FACT, "meaning+normalization+scope_all_correct"
    if meaning and not normalized:
        return Label.WRONG_NORMALIZATION, "meaning_supported+normalization_incorrect"
    if meaning and normalized and not scope:
        return Label.WRONG_SCOPE, "meaning+normalization_correct+scope_incorrect"
    return Label.PARTIALLY_SUPPORTED, "meaning_supported+other_defect"


DOCUMENT_KEYS = {
    "src_29af34430672001d": "CHP_AURAL_BREVITY",
    "src_b1ec55369bd8b386": "IN_ISP_COMMUNICATIONS",
    "src_b2f7f6d601d0512c": "CHI_CPD_DIRECTIVE",
    "src_c8b6dc4156470007": "PHL_PPD_DIRECTIVE_7_1",
}


def build_gold(audit_path: Path, facts_path: Path, sources_path: Path) -> list[GoldRecord]:
    facts = {json.loads(line)["fact_id"]: json.loads(line) for line in audit_lines(facts_path)}
    hashes = {}
    for line in audit_lines(sources_path):
        row = json.loads(line)
        hashes[row["source_id"]] = row.get("document_hash")
    out: list[GoldRecord] = []
    for line in audit_lines(audit_path):
        a = json.loads(line)
        f = facts.get(a["fact_id"])
        if f is None:
            continue
        label, rule = derive_label(a)
        out.append(
            GoldRecord(
                gold_id=f"gold_{a['audit_index']:04d}",
                fact_id=a["fact_id"],
                agency_id=a["agency_id"],
                source_id=a["source_id"],
                document_key=DOCUMENT_KEYS.get(a["source_id"], a["source_id"]),
                fact_type=a["fact_type"],
                key=a["key"],
                locator=a["locator"],
                expected_value=f["value"],
                excerpt=f.get("excerpt") or "",
                label=label,
                failure_class=classify_failure(a.get("reason") or "", supported=bool(a.get("exact_meaning_supported"))),
                rationale=a.get("reason") or "",
                reviewer=a.get("reviewer") or "unknown",
                review_method=a.get("review_method") or "unknown",
                reviewed_at=a.get("reviewed_at") or "",
                source_document_hash=hashes.get(a["source_id"]),
                derivation_rule=rule,
                original_flags={
                    k: a.get(k)
                    for k in (
                        "exact_meaning_supported",
                        "normalized_metadata_correct",
                        "agency_attribution_correct",
                        "applicability_scope_correct",
                        "locator_correct",
                        "source_authoritative",
                        "source_current",
                        "safe_expected_answer",
                        "decision",
                        "human_review",
                    )
                },
            )
        )
    return out


def audit_lines(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield line


def write_gold(records: list[GoldRecord], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for r in records:
            handle.write(json.dumps(r.to_dict(), sort_keys=True) + "\n")
    return len(records)


def load_gold(path: Path) -> list[GoldRecord]:
    return [GoldRecord(**json.loads(line)) for line in audit_lines(path)]
