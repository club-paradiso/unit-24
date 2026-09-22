"""Compute real-document metrics from the completed adjudication worksheet.

Refuses to report a precision whose population contains an unadjudicated field, and reports
recall only against a reviewer-supplied inventory of facts the document actually contains.
Synthetic-corpus figures are never mixed in.

    uv run python scripts/score_adjudication.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from radiocorpus.evaluation.adjudication import read_missed, read_records, score
from radiocorpus.extraction.codes import PARSER_VERSION as CODE_V
from radiocorpus.extraction.phonetics import PARSER_VERSION as PHON_V
from radiocorpus.extraction.procedures import PARSER_VERSION as PROC_V

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "adjudication"
OUT = ROOT / "data" / "evaluation"


def main() -> int:
    worksheet = IN / "real_document_worksheet.jsonl"
    if not worksheet.exists():
        print(f"missing {worksheet}. Run scripts/build_adjudication_worksheet.py first.")
        return 1
    records = read_records(worksheet)
    missed = read_missed(IN / "missed_facts.jsonl")
    result = score(
        records,
        missed,
        current_parser_versions={"code_meaning": CODE_V, "phonetic_letter": PHON_V, "procedure_rule": PROC_V},
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "real_document_adjudicated_metrics.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "per_document"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
