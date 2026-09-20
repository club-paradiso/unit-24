"""Metrics reported per fact family and per document. No flattering aggregate."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from radiocorpus.evaluation.gold import Label
from radiocorpus.evaluation.replay import ReplayOutcome

# Labels that mean "the previous candidate should not have been asserted as it stood".
UNSUPPORTED_LABELS = {Label.FALSE_POSITIVE, Label.INSUFFICIENT_CONTEXT}
SUPPORTED_MEANING_LABELS = {Label.TRUE_FACT, Label.WRONG_SCOPE, Label.WRONG_NORMALIZATION, Label.PARTIALLY_SUPPORTED}


def _bucket(outcomes: list[ReplayOutcome]) -> dict[str, Any]:
    emitted = [o for o in outcomes if o.reemitted]
    emitted_supported = [o for o in emitted if o.label in SUPPORTED_MEANING_LABELS]
    emitted_unsupported = [o for o in emitted if o.label in UNSUPPORTED_LABELS]
    baseline_supported = [o for o in outcomes if o.label in SUPPORTED_MEANING_LABELS]
    true_facts = [o for o in outcomes if o.label == Label.TRUE_FACT]
    complete_ctx = [o for o in emitted if o.context_complete is not False]
    complete_ctx_supported = [o for o in complete_ctx if o.label in SUPPORTED_MEANING_LABELS]
    return {
        "audited_candidates": len(outcomes),
        "baseline_emitted": len(outcomes),
        "baseline_meaning_supported": len(baseline_supported),
        "baseline_meaning_precision": _ratio(len(baseline_supported), len(outcomes)),
        "baseline_complete_facts": len(true_facts),
        "baseline_complete_fact_precision": _ratio(len(true_facts), len(outcomes)),
        "replay_emitted": len(emitted),
        "replay_meaning_supported": len(emitted_supported),
        "replay_meaning_precision": _ratio(len(emitted_supported), len(emitted)),
        "replay_unsupported_still_emitted": len(emitted_unsupported),
        "false_positives_eliminated": len([o for o in outcomes if o.label in UNSUPPORTED_LABELS and not o.reemitted]),
        "false_positives_total_in_gold": len([o for o in outcomes if o.label in UNSUPPORTED_LABELS]),
        "true_facts_retained_text_only": len([o for o in true_facts if o.reemitted]),
        "true_facts_total_in_gold": len(true_facts),
        "context_complete_emitted": len(complete_ctx),
        "context_complete_meaning_precision": _ratio(len(complete_ctx_supported), len(complete_ctx)),
    }


def _ratio(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def summarise(outcomes: list[ReplayOutcome]) -> dict[str, Any]:
    by_family: dict[str, list[ReplayOutcome]] = defaultdict(list)
    by_doc: dict[str, list[ReplayOutcome]] = defaultdict(list)
    by_doc_family: dict[tuple[str, str], list[ReplayOutcome]] = defaultdict(list)
    failure_elimination: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "eliminated": 0})
    for o in outcomes:
        by_family[o.fact_type].append(o)
        by_doc[o.document_key].append(o)
        by_doc_family[(o.document_key, o.fact_type)].append(o)
        if o.label in UNSUPPORTED_LABELS:
            failure_elimination[o.failure_class]["total"] += 1
            if not o.reemitted:
                failure_elimination[o.failure_class]["eliminated"] += 1
    return {
        "replay_mode": outcomes[0].replay_mode if outcomes else "none",
        "caveat": (
            "Replay measures whether the current parsers repeat claims the previous parser made on the same "
            "flattened excerpt. Rejecting a labelled false positive is evidence of improved precision. "
            "Retention of a true fact is a lower bound, not recall. Recall on the real documents is not "
            "measurable here because the documents are not retrievable in this environment."
        ),
        "overall": _bucket(outcomes),
        "by_fact_family": {k: _bucket(v) for k, v in sorted(by_family.items())},
        "by_document": {k: _bucket(v) for k, v in sorted(by_doc.items())},
        "by_document_and_family": {f"{d}|{f}": _bucket(v) for (d, f), v in sorted(by_doc_family.items())},
        "failure_class_elimination": {
            k: {**v, "elimination_rate": _ratio(v["eliminated"], v["total"])} for k, v in sorted(failure_elimination.items())
        },
    }
