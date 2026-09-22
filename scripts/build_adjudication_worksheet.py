"""Build the independent adjudication worksheet for the real validation documents.

The worksheet is the instrument that keeps the parser from defining its own ground truth:
one row per candidate, one verdict per claim that candidate makes, every verdict starting
UNADJUDICATED. A reviewer fills it in against the source documents.

Two inputs are possible, and which one is used is recorded in the output:

* ``data/evaluation/real_document_candidates.jsonl`` - candidates from the *current* parsers,
  written by scripts/run_layout_validation.py once the documents are present.
* ``data/audit/fact_audit.jsonl`` - the previous independent review. Its verdicts are restated
  into the richer instrument, so the worksheet starts from what was genuinely decided and
  shows precisely which claims were never judged.

    uv run python scripts/build_adjudication_worksheet.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from radiocorpus.evaluation.adjudication import (
    mark_absent_claims,
    seed_from_audit,
    seeding_coverage,
    worksheet_from_candidates,
    write_records,
)
from radiocorpus.evaluation.gold import DOCUMENT_KEYS, audit_lines

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "audit"
EVAL = ROOT / "data" / "evaluation"
OUT = ROOT / "data" / "adjudication"


def _source_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    path = AUDIT / "real_sources.jsonl"
    if path.exists():
        for line in audit_lines(path):
            row = json.loads(line)
            if row.get("document_hash"):
                out[row["source_id"]] = row["document_hash"]
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    live = EVAL / "real_document_candidates.jsonl"
    rows = [json.loads(line) for line in audit_lines(live)] if live.exists() else []
    parsed = [r for r in rows if r.get("document")]

    if parsed:
        hashes = {}
        metrics = EVAL / "real_document_metrics.json"
        if metrics.exists():
            summary = json.loads(metrics.read_text()).get("documents", {})
            hashes = {k: v.get("document_sha256", "") for k, v in summary.items()}
        records = worksheet_from_candidates(parsed, hashes=hashes)
        origin = "current parsers, via data/evaluation/real_document_candidates.jsonl"
    else:
        audit_rows = [json.loads(line) for line in audit_lines(AUDIT / "fact_audit.jsonl")]
        facts = {json.loads(line)["fact_id"]: json.loads(line) for line in audit_lines(AUDIT / "real_facts.jsonl")}
        records = seed_from_audit(audit_rows, facts, document_keys=DOCUMENT_KEYS, hashes=_source_hashes())
        origin = "previous independent review, restated from data/audit/fact_audit.jsonl"

    # Second pass: decide the claims the candidates never made. This needs no document — a
    # claim absent from a candidate is a fact about the candidate — and it never overwrites a
    # reviewer's verdict. Everything it decides is recorded per record as mechanical.
    mechanical = {name: 0 for name in sorted({f for r in records for f in r.required_fields()})}
    for record in records:
        for name in mark_absent_claims(record):
            mechanical[name] = mechanical.get(name, 0) + 1

    write_records(records, OUT / "real_document_worksheet.jsonl")
    coverage = seeding_coverage(records)
    coverage["origin"] = origin
    coverage["decided_by_absence"] = {k: v for k, v in sorted(mechanical.items()) if v}
    (OUT / "worksheet_coverage.json").write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(records)} adjudication records from: {origin}")
    print(f"fully adjudicated: {coverage['fully_adjudicated']} / {coverage['records']}")
    for name, count in coverage["decided_by_absence"].items():
        print(f"  ABSENT FROM CANDIDATE {name:28s} {count:3d} (decided without a document)")
    for name, stats in coverage["per_field"].items():
        if stats["unadjudicated"]:
            print(f"  STILL UNADJUDICATED   {name:28s} {stats['unadjudicated']:3d} / {stats['applicable']:3d} applicable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
