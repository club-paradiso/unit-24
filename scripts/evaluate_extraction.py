"""Produce the extraction evaluation package.

Writes machine-readable artifacts under ``data/evaluation/`` for independent audit:

* ``gold_labels.jsonl``       correction labels derived from the committed independent review
* ``replay_outcomes.jsonl``   per-candidate replay result under the current parsers
* ``metrics_replay.json``     per fact family and per document, with the baseline alongside
* ``lodo.json``               leave-one-document-out folds
* ``fixture_truth.json``      exhaustive ground truth for the synthetic layout fixtures
* ``fixture_eval.json``       precision AND recall on the fixtures (recall is valid here only
                              because the fixtures are exhaustively known by construction)
* ``fixture_candidates.jsonl`` every candidate the fixtures produce, for inspection

Run: uv run python scripts/evaluate_extraction.py
"""

from __future__ import annotations

import json
from pathlib import Path

from radiocorpus.evaluation.gold import build_gold, write_gold
from radiocorpus.evaluation.metrics import summarise
from radiocorpus.evaluation.replay import replay, replay_page_groups
from radiocorpus.extraction.codes import PARSER_VERSION as CODE_V
from radiocorpus.extraction.codes import parse_codes
from radiocorpus.extraction.phonetics import PARSER_VERSION as PHON_V
from radiocorpus.extraction.phonetics import describe_alphabet, parse_phonetics
from radiocorpus.extraction.procedures import PARSER_VERSION as PROC_V
from radiocorpus.extraction.procedures import parse_procedures
from radiocorpus.layout.backends import layout_for
from radiocorpus.layout.model import LAYOUT_VERSION

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "audit"
OUT = ROOT / "data" / "evaluation"
FIXTURES = ROOT / "data" / "fixtures" / "layout"

# Exhaustive ground truth for the synthetic fixtures. These are known completely because the
# fixtures were constructed here; that is the only reason recall is meaningful below.
FIXTURE_TRUTH: dict[str, dict] = {
    "lx01_multicolumn_code_table.pdf": {
        "note": "Four independent columns. Column 2 entries wrap, so their remainder lands beside the next code.",
        "code_meaning": {
            "10-2": "Reception good",
            "10-4": "Message received",
            "10-5": "Relay message",
            "10-6": "Busy stand by",
            "10-7": "Out of service",
            "10-8": "In service",
            "10-36A": "Confidential information subject possibly armed",
            "10-36F": "Confidential information possible felony wants",
            "10-37": "What time is it",
            "11-84": "Direct traffic",
            "11-85": "Tow truck",
            "11-86": "Bomb threat",
            "11-87": "Bomb found",
            "11-98": "Meet",
        },
        "phonetic_letter": {},
        "procedure_rule": [],
        "must_not_emit_codes": ["23152", "23153", "187", "211"],
    },
    "lx02_revision_date_table.pdf": {
        "note": "Revision history whose dates are shaped like eleven-codes.",
        "code_meaning": {},
        "phonetic_letter": {},
        "procedure_rule": [],
        "must_not_emit_codes": ["11-18", "11-13", "12-05", "10-17", "09-11"],
    },
    "lx03_enumerated_headings.pdf": {
        "note": "Enumerated section headings shaped like phonetic pairs.",
        "code_meaning": {},
        "phonetic_letter": {},
        "procedure_rule": [],
        "must_not_emit_letters": ["A", "B", "C", "D"],
    },
    "lx04_local_alphabet_divergence.pdf": {
        "note": "Local alphabet matching APCO on 25 letters, diverging on Z.",
        "code_meaning": {},
        "phonetic_letter": {
            "A": "ADAM", "B": "BOY", "C": "CHARLES", "D": "DAVID", "E": "EDWARD", "F": "FRANK",
            "G": "GEORGE", "H": "HENRY", "I": "IDA", "J": "JOHN", "K": "KING", "L": "LINCOLN",
            "M": "MARY", "N": "NORA", "O": "OCEAN", "P": "PAUL", "Q": "QUEEN", "R": "ROBERT",
            "S": "SAM", "T": "TOM", "U": "UNION", "V": "VICTOR", "W": "WILLIAM", "X": "XRAY",
            "Y": "YOUNG", "Z": "ZULU",
        },
        "procedure_rule": [],
        "required_divergence": {"Z": "ZULU"},
    },
    "lx05_footer_code_token.pdf": {
        "note": "Repeated footer carrying a code-shaped token.",
        "code_meaning": {},
        "phonetic_letter": {},
        "procedure_rule": [],
        "must_not_emit_codes": ["10-42"],
    },
    "lx06_page_boundary_rule.pdf": {
        "note": "Rule whose qualifying exception is on the following page.",
        "code_meaning": {},
        "phonetic_letter": {},
        "procedure_rule": ["acknowledgement"],
        "required_context_after_contains": "need not repeat",
    },
    "lx07_non_radio_copy_and_plate.pdf": {
        "note": "'copy' as a document and 'plate' as impounded property.",
        "code_meaning": {},
        "phonetic_letter": {},
        "procedure_rule": [],
    },
    "lx08_repeated_header.pdf": {
        "note": "Banner repeated on every page is furniture; the body rule is content.",
        "code_meaning": {},
        "phonetic_letter": {},
        "procedure_rule": ["location_address"],
    },
    "lx09_single_column_narrative.pdf": {
        "note": "Ordinary one-column policy page; column detection must not fire.",
        "code_meaning": {},
        "phonetic_letter": {},
        "procedure_rule": ["location_address"],
        "required_column_count": 1,
    },
}


def evaluate_fixtures() -> tuple[dict, list[dict]]:
    results: dict[str, dict] = {}
    candidates: list[dict] = []
    totals = {
        "code_tp": 0, "code_fp": 0, "code_fn": 0,
        "phon_tp": 0, "phon_fp": 0, "phon_fn": 0,
        "proc_tp": 0, "proc_fp": 0, "proc_fn": 0,
        "layout_failures": 0,
    }
    for name, truth in sorted(FIXTURE_TRUTH.items()):
        path = FIXTURES / name
        if not path.exists():
            results[name] = {"error": "fixture missing"}
            continue
        layout = layout_for(path.read_bytes(), "application/pdf")
        codes = parse_codes(layout)
        phon = parse_phonetics(layout)
        procs = parse_procedures(layout)
        for c in codes:
            candidates.append({"fixture": name, "family": "code_meaning", "code": c.code, "meaning": c.meaning,
                               "locator": c.locator, "structural_reason": c.structural_reason, "evidence": list(c.evidence)})
        for p in phon:
            candidates.append({"fixture": name, "family": "phonetic_letter", "letter": p.letter, "word": p.word,
                               "locator": p.locator, "structural_reason": p.structural_reason})
        for r in procs:
            candidates.append({"fixture": name, "family": "procedure_rule", "procedure": r.procedure, "locator": r.locator,
                               "medium": r.medium, "context_complete": r.context_complete, "crosses_page": r.crosses_page,
                               "section_heading": r.section_heading, "rule_text": r.rule_text})

        want_codes = truth.get("code_meaning", {})
        got_codes = {c.code: c.meaning for c in codes}
        code_tp = sum(1 for k, v in want_codes.items() if got_codes.get(k) == v)
        code_wrong_meaning = {k: (want_codes[k], got_codes[k]) for k in want_codes if k in got_codes and got_codes[k] != want_codes[k]}
        code_fp = len([k for k in got_codes if k not in want_codes]) + len(code_wrong_meaning)
        code_fn = len([k for k in want_codes if k not in got_codes]) + len(code_wrong_meaning)

        want_ph = truth.get("phonetic_letter", {})
        got_ph = {p.letter: p.word for p in phon}
        phon_tp = sum(1 for k, v in want_ph.items() if got_ph.get(k) == v)
        phon_fp = len([k for k in got_ph if k not in want_ph or got_ph[k] != want_ph.get(k)])
        phon_fn = len([k for k in want_ph if got_ph.get(k) != want_ph[k]])

        want_proc = list(truth.get("procedure_rule", []))
        got_proc = [r.procedure for r in procs]
        proc_tp = sum(1 for p in want_proc if p in got_proc)
        proc_fp = len([p for p in got_proc if p not in want_proc])
        proc_fn = len([p for p in want_proc if p not in got_proc])

        checks: dict[str, object] = {}
        for forbidden in truth.get("must_not_emit_codes", []):
            checks[f"must_not_emit_code:{forbidden}"] = not any(forbidden in c.code for c in codes)
        for forbidden in truth.get("must_not_emit_letters", []):
            checks[f"must_not_emit_letter:{forbidden}"] = forbidden not in got_ph
        if "required_divergence" in truth:
            report = describe_alphabet(phon)
            checks["divergence_preserved"] = all(report.mappings.get(k) == v for k, v in truth["required_divergence"].items())
            checks["divergence_reported"] = bool(report.divergences)
            checks["label_is_descriptive"] = report.label
        if "required_column_count" in truth:
            checks["column_count"] = max(p.column_count for p in layout.pages) == truth["required_column_count"]
        if "required_context_after_contains" in truth:
            checks["context_after_carries_exception"] = any(
                truth["required_context_after_contains"] in (r.context_after or "") for r in procs
            )
        failed = [k for k, v in checks.items() if v is False]
        totals["layout_failures"] += len(failed)
        for key, val in (("code_tp", code_tp), ("code_fp", code_fp), ("code_fn", code_fn),
                         ("phon_tp", phon_tp), ("phon_fp", phon_fp), ("phon_fn", phon_fn),
                         ("proc_tp", proc_tp), ("proc_fp", proc_fp), ("proc_fn", proc_fn)):
            totals[key] += val
        results[name] = {
            "note": truth.get("note"),
            "pages": len(layout.pages),
            "columns": max(p.column_count for p in layout.pages),
            "blocks_kept": len(layout.included_blocks()),
            "blocks_excluded": len([b for p in layout.pages for b in p.blocks if b.excluded]),
            "code": {"tp": code_tp, "fp": code_fp, "fn": code_fn, "wrong_meaning": code_wrong_meaning},
            "phonetic": {"tp": phon_tp, "fp": phon_fp, "fn": phon_fn},
            "procedure": {"tp": proc_tp, "fp": proc_fp, "fn": proc_fn, "emitted": got_proc},
            "structural_checks": checks,
            "failed_checks": failed,
        }

    def pr(tp: int, fp: int, fn: int) -> dict:
        return {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(tp / (tp + fp), 4) if (tp + fp) else None,
            "recall": round(tp / (tp + fn), 4) if (tp + fn) else None,
        }

    summary = {
        "ground_truth": "exhaustive_by_construction",
        "recall_valid": True,
        "code_meaning": pr(totals["code_tp"], totals["code_fp"], totals["code_fn"]),
        "phonetic_letter": pr(totals["phon_tp"], totals["phon_fp"], totals["phon_fn"]),
        "procedure_rule": pr(totals["proc_tp"], totals["proc_fp"], totals["proc_fn"]),
        "failed_structural_checks": totals["layout_failures"],
        "per_fixture": results,
    }
    return summary, candidates


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gold = build_gold(AUDIT / "fact_audit.jsonl", AUDIT / "real_facts.jsonl", AUDIT / "real_sources.jsonl")
    write_gold(gold, OUT / "gold_labels.jsonl")

    outcomes = replay(gold)
    grouped = replay_page_groups(gold)
    with (OUT / "replay_outcomes.jsonl").open("w", encoding="utf-8") as handle:
        for o in outcomes + grouped:
            handle.write(json.dumps(o.to_dict(), sort_keys=True) + "\n")

    versions = {
        "layout_version": LAYOUT_VERSION,
        "code_parser_version": CODE_V,
        "phonetic_parser_version": PHON_V,
        "procedure_parser_version": PROC_V,
    }
    metrics = {
        "isolated_excerpt": summarise(outcomes),
        "page_group_reconstruction": summarise(grouped),
        "parser_versions": versions,
        "mode_note": (
            "isolated_excerpt presents one flattened line with no structural evidence; a structure-gated "
            "parser declines it by design. page_group_reconstruction restores the weakest legitimate text "
            "signal (a run of sibling records) but still supplies no geometry. Neither mode substitutes for "
            "parsing the real documents, which are not retrievable in this environment."
        ),
    }
    (OUT / "metrics_replay.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")

    # Leave-one-document-out: each fold holds out one document entirely. No parser rule is
    # conditioned on a document or agency, so a fold is a genuine held-out measurement.
    docs = sorted({o.document_key for o in outcomes})
    folds = {}
    for held in docs:
        dev = [o for o in outcomes if o.document_key != held]
        test = [o for o in outcomes if o.document_key == held]
        folds[held] = {
            "development_documents": [d for d in docs if d != held],
            "development": summarise(dev)["overall"],
            "held_out": summarise(test)["overall"],
        }
    (OUT / "lodo.json").write_text(
        json.dumps(
            {
                "method": "leave_one_document_out",
                "note": (
                    "Parsers contain no agency-specific or document-specific branches, enforced by "
                    "tests/test_layout_extraction.py::test_no_agency_specific_parser_branches. Each fold "
                    "therefore reports held-out behaviour of rules developed against the other documents."
                ),
                "parser_versions": versions,
                "folds": folds,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    fixture_summary, fixture_candidates = evaluate_fixtures()
    fixture_summary["parser_versions"] = versions
    (OUT / "fixture_eval.json").write_text(json.dumps(fixture_summary, indent=2, sort_keys=True) + "\n")
    (OUT / "fixture_truth.json").write_text(json.dumps(FIXTURE_TRUTH, indent=2, sort_keys=True) + "\n")
    with (OUT / "fixture_candidates.jsonl").open("w", encoding="utf-8") as handle:
        for c in fixture_candidates:
            handle.write(json.dumps(c, sort_keys=True) + "\n")

    print(f"gold={len(gold)} replay={len(outcomes)} fixtures={len(FIXTURE_TRUTH)} candidates={len(fixture_candidates)}")
    for mode in ("isolated_excerpt", "page_group_reconstruction"):
        print(f"--- {mode} ---")
        print(json.dumps(metrics[mode]["by_fact_family"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
