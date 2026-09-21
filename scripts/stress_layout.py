"""Produce the randomized-geometry evaluation artifacts.

Writes under ``data/evaluation/``:

* ``layout_stress.json``          per-document results and the corpus summary
* ``threshold_sensitivity.json``  column detection under every threshold combination

Both are generated output, committed for the same reason the rest of ``data/evaluation`` is:
an auditor can read them without a network, and this command regenerates them exactly.

Run: uv run python scripts/stress_layout.py [documents] [sweep-documents]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from radiocorpus.evaluation.sensitivity import sweep
from radiocorpus.evaluation.stress import run
from radiocorpus.extraction.codes import PARSER_VERSION as CODE_V
from radiocorpus.extraction.phonetics import PARSER_VERSION as PHON_V
from radiocorpus.extraction.procedures import PARSER_VERSION as PROC_V
from radiocorpus.layout.model import LAYOUT_VERSION, layout_code_fingerprint

OUT = Path(__file__).resolve().parents[1] / "data" / "evaluation"

PROVENANCE = {
    "layout_version": LAYOUT_VERSION,
    "layout_code_fingerprint": layout_code_fingerprint(),
    "code_parser_version": CODE_V,
    "phonetic_parser_version": PHON_V,
    "procedure_parser_version": PROC_V,
}

CAVEAT = (
    "Synthetic geometry only. Recall is meaningful here solely because this corpus was "
    "generated from a plan that is its own ground truth. It is not evidence about any real "
    "document: the four real validation documents remain unretrieved."
)


def main() -> None:
    documents = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    sweep_documents = int(sys.argv[2]) if len(sys.argv) > 2 else 120

    results, summary = run(range(1, documents + 1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "layout_stress.json").write_text(
        json.dumps(
            {
                "note": CAVEAT,
                "seeds": f"1..{documents}",
                "parser_versions": PROVENANCE,
                "summary": summary,
                "documents_with_any_defect": sorted(
                    r.seed
                    for r in results
                    if r.code_fp or r.code_fn or r.letter_fp or r.letter_fn or r.decoy_emitted
                    or r.procedure_false_positive or r.column_verdict == "invented_columns" or r.layout_error
                ),
                "results": [r.as_dict() for r in results],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    sensitivity = sweep(range(1, sweep_documents + 1))
    sensitivity["note"] = f"{sensitivity['note']} {CAVEAT}"
    sensitivity["parser_versions"] = PROVENANCE
    (OUT / "threshold_sensitivity.json").write_text(json.dumps(sensitivity, indent=2, sort_keys=True) + "\n")

    print(f"layout_stress.json: {summary['documents']} documents")
    print(f"  column detection    {summary['column_detection']} (invented: {summary['invented_columns']})")
    print(f"  code_meaning        {summary['code_meaning']}")
    print(f"  phonetic_letter     {summary['phonetic_letter']}")
    print(f"  decoys emitted      {summary['decoy_dates_emitted_as_codes']}")
    print(f"  procedure FP docs   {summary['procedure_false_positive_documents']}")
    print(f"threshold_sensitivity.json: {sensitivity['documents']} documents, "
          f"best usable {sensitivity['best_usable_setting']}, in use {sensitivity['in_use']}")


if __name__ == "__main__":
    main()
