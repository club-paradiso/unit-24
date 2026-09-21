"""Run the layout stack over real third-party PDFs and record what it does.

Every other PDF this repository parses was written by this repository. That makes the whole
fixture corpus a test of the parsers against one PDF producer — ours. These documents come
from someone else's tooling, and running them found two defects nothing synthetic had:
a letter-keyed code table emitted as a phonetic alphabet, and a document with no extractable
text returning empty without saying so.

This reports robustness, not accuracy. There is no ground truth for these documents and none
is claimed: the counts below say what the stack did, not whether it was right. The only hard
assertion is the one in the tests — that these documents yield no radio facts at all, because
they contain none.

    uv run python scripts/probe_real_documents.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from radiocorpus.extraction.codes import parse_codes
from radiocorpus.extraction.phonetics import parse_phonetics
from radiocorpus.extraction.procedures import parse_procedures
from radiocorpus.extraction.text import OCRRequired
from radiocorpus.layout.backends import layout_for
from radiocorpus.layout.model import LAYOUT_VERSION, layout_code_fingerprint

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures" / "real"
OUT = ROOT / "data" / "evaluation"


def main() -> int:
    manifest = json.loads((FIXTURES / "MANIFEST.json").read_text())
    results: dict[str, dict] = {}
    failed = 0
    for entry in manifest["documents"]:
        path = FIXTURES / entry["filename"]
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry["sha256"]:
            results[entry["filename"]] = {"status": "HASH_MISMATCH", "expected": entry["sha256"], "actual": digest}
            print(f"REFUSING {entry['filename']}: hash mismatch")
            failed += 1
            continue
        try:
            layout = layout_for(data, "application/pdf", document_hash=f"sha256:{digest}")
        except OCRRequired as error:
            results[entry["filename"]] = {"status": "OCR_REQUIRED", "detail": str(error)}
            continue
        codes, phon, procs = parse_codes(layout), parse_phonetics(layout), parse_procedures(layout)
        results[entry["filename"]] = {
            "status": "PARSED",
            "issuing_authority": entry["issuing_authority"],
            "licence": entry["licence"],
            "sha256": digest,
            "pages": len(layout.pages),
            "columns_per_page": [p.column_count for p in layout.pages],
            "blocks_kept": len(layout.included_blocks()),
            "blocks_excluded": len([b for p in layout.pages for b in p.blocks if b.excluded]),
            "warnings": list(layout.warnings),
            "text_extraction_methods": sorted(layout.text_extraction_methods),
            "candidates": {"code_meaning": len(codes), "phonetic_letter": len(phon), "procedure_rule": len(procs)},
        }
        if codes or phon or procs:
            failed += 1
            print(f"UNEXPECTED {entry['filename']} emitted radio facts: "
                  f"{len(codes)} codes, {len(phon)} letters, {len(procs)} procedures")
    payload = {
        "note": (
            "Robustness probe over real third-party PDFs. No ground truth exists for these "
            "documents and no precision is claimed. They are not radio-protocol sources and are "
            "never ingested as evidence about any agency."
        ),
        "parser_versions": {
            "layout_version": LAYOUT_VERSION,
            "layout_code_fingerprint": layout_code_fingerprint(),
        },
        "documents": results,
        "expected_radio_facts": 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "real_pdf_probe.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
