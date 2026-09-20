"""Parse the four verified validation documents and write real-document metrics.

This is the step that the build environment could not run. It re-checks each file's SHA-256
before parsing, so a swapped document cannot enter the measurement.

    uv run python scripts/run_layout_validation.py

Output: data/evaluation/real_document_candidates.jsonl and
        data/evaluation/real_document_metrics.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from radiocorpus.extraction.codes import PARSER_VERSION as CODE_V
from radiocorpus.extraction.codes import parse_codes
from radiocorpus.extraction.phonetics import PARSER_VERSION as PHON_V
from radiocorpus.extraction.phonetics import describe_alphabet, parse_phonetics
from radiocorpus.extraction.procedures import PARSER_VERSION as PROC_V
from radiocorpus.extraction.procedures import parse_procedures
from radiocorpus.layout.backends import layout_for
from radiocorpus.layout.model import LAYOUT_VERSION, layout_code_fingerprint

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "raw" / "layout-validation"
OUT = ROOT / "data" / "evaluation"


def main() -> int:
    manifest = json.loads((DIR / "MANIFEST.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    summary: dict[str, dict] = {}
    missing: list[str] = []
    for doc in manifest["documents"]:
        path = DIR / doc["filename"]
        if not path.exists():
            missing.append(doc["key"])
            summary[doc["key"]] = {"status": "MISSING", "note": doc.get("retrieval_error")}
            continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != doc["expected_sha256"]:
            summary[doc["key"]] = {"status": "HASH_MISMATCH", "expected": doc["expected_sha256"], "actual": digest}
            print(f"REFUSING {doc['key']}: hash mismatch; this is a different document")
            continue
        layout = layout_for(data, "application/pdf", document_hash=f"sha256:{digest}")
        codes, phon, procs = parse_codes(layout), parse_phonetics(layout), parse_procedures(layout)
        report = describe_alphabet(phon)
        for c in codes:
            rows.append({"document": doc["key"], "family": "code_meaning", "code": c.code, "meaning": c.meaning,
                         "locator": c.locator, "structural_reason": c.structural_reason,
                         "continuation_lines": c.continuation_lines, "evidence": list(c.evidence), "excerpt": c.excerpt})
        for p in phon:
            rows.append({"document": doc["key"], "family": "phonetic_letter", "letter": p.letter, "word": p.word,
                         "locator": p.locator, "structural_reason": p.structural_reason, "excerpt": p.excerpt})
        for r in procs:
            rows.append({"document": doc["key"], "family": "procedure_rule", "procedure": r.procedure, "locator": r.locator,
                         "medium": r.medium, "context_complete": r.context_complete, "crosses_page": r.crosses_page,
                         "has_condition": r.has_condition, "has_exception": r.has_exception,
                         "section_heading": r.section_heading, "rule_text": r.rule_text,
                         "context_before": r.context_before, "context_after": r.context_after})
        summary[doc["key"]] = {
            "status": "PARSED",
            "pages": len(layout.pages),
            "expected_page_count": doc.get("expected_page_count"),
            "page_count_matches": len(layout.pages) == doc.get("expected_page_count"),
            "max_columns": max(p.column_count for p in layout.pages),
            "blocks_kept": len(layout.included_blocks()),
            "blocks_excluded": len([b for p in layout.pages for b in p.blocks if b.excluded]),
            "code_candidates": len(codes),
            "phonetic_candidates": len(phon),
            "procedure_candidates": len(procs),
            "procedure_context_complete": sum(1 for r in procs if r.context_complete),
            "alphabet": report.to_dict() if phon else None,
            "text_extraction_methods": sorted(layout.text_extraction_methods),
        }
    with (OUT / "real_document_candidates.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    (OUT / "real_document_metrics.json").write_text(
        json.dumps(
            {
                "parser_versions": {
                    "layout_version": LAYOUT_VERSION,
                    "layout_code_fingerprint": layout_code_fingerprint(),
                    "code_parser_version": CODE_V,
                    "phonetic_parser_version": PHON_V,
                    "procedure_parser_version": PROC_V,
                },
                "documents": summary,
                "note": (
                    "Candidate counts are not precision. Adjudicate data/evaluation/real_document_candidates.jsonl "
                    "against the source documents before quoting any precision figure."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if missing:
        print(f"\n{len(missing)} document(s) missing: {missing}. Run scripts/fetch_layout_validation.py first.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
