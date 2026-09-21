"""How much of real policy prose the procedure decomposition can actually take apart.

The randomized corpus reports 1.000 precision and recall for the decomposition, and that
number says nothing about real documents: the sentences were written by the same code that
scores them, in shapes it was built to produce. The question that matters is **coverage** —
what fraction of the sentences an agency actually writes yields an actor, an act and an
object at all.

That question can be answered now, without the four blocked PDFs, because a decomposition is
a function of the sentence alone. Two samples of genuinely real prose are available:

* **Rule sentences from the real corpus.** ``data/audit/real_facts.jsonl`` holds the verbatim
  ``rule_text`` the previous parser read out of the four validation documents and several
  other retrieved sources. The sentences are real even though the documents are gone.
* **A real third-party document.** The committed FBI NIBRS data dictionary, parsed here, for
  every sentence carrying a modal. Out of domain by design: it tests the *shapes* real
  government prose takes, not radio content.

What this measures and what it does not: coverage, and the reasons for refusal. Not accuracy.
Whether a located actor is the *right* actor still needs a reviewer — but unlike every other
real-document question in this project, the evidence is the sentence itself, and the sentence
is present. Selection bias is real and stated: these are sentences an earlier parser chose to
emit, not a random sample of the documents.

    uv run python scripts/probe_decomposition_coverage.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

from radiocorpus.evaluation.gold import DOCUMENT_KEYS, audit_lines
from radiocorpus.extraction.decomposition import MODAL, decompose
from radiocorpus.extraction.procedures import split_sentences
from radiocorpus.layout.backends import layout_for

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "audit"
REAL_FIXTURES = ROOT / "data" / "fixtures" / "real"
OUT = ROOT / "data" / "evaluation"
EXAMPLES_PER_REASON = 3


def _reason(decomposition) -> str:
    """The first evidence line that explains a refusal, or why it succeeded."""
    if decomposition.complete:
        return "complete"
    for note in decomposition.evidence:
        head = note.split(":", 1)[0]
        if head in {
            "no_modal", "no_subject_before_modal", "subject_too_long", "second_modal_inside_subject",
            "subject_is_a_date_label", "no_communication_verb_after_modal", "nearer_non_communication_verb",
            "communication_verb_too_far_from_modal", "no_noun_phrase_after_verb",
            "content_marker_without_object", "ambiguous_of_phrase",
        }:
            return head
    missing = [
        name for name, value in (
            ("actor", decomposition.actor),
            ("action", decomposition.communication_action),
            ("object", decomposition.governed_object),
        ) if value is None
    ]
    return "missing:" + "+".join(missing) if missing else "incomplete_unclassified"


def _score(sentences: list[tuple[str, str]], label: str, note: str) -> dict:
    reasons: collections.Counter[str] = collections.Counter()
    examples: dict[str, list[dict]] = collections.defaultdict(list)
    located = collections.Counter()
    for origin, sentence in sentences:
        d = decompose(sentence)
        reason = _reason(d)
        reasons[reason] += 1
        for name, span in (("actor", d.actor), ("action", d.communication_action), ("object", d.governed_object)):
            if span is not None:
                located[name] += 1
        if len(examples[reason]) < EXAMPLES_PER_REASON:
            examples[reason].append({
                "origin": origin,
                "sentence": sentence[:240],
                "actor": d.actor.text if d.actor else None,
                "action": d.communication_action.text if d.communication_action else None,
                "object": d.governed_object.text if d.governed_object else None,
            })
    total = len(sentences)
    return {
        "label": label,
        "note": note,
        "sentences": total,
        "fully_decomposed": reasons["complete"],
        "coverage": round(reasons["complete"] / total, 4) if total else None,
        "elements_located": {k: {"n": v, "rate": round(v / total, 4)} for k, v in sorted(located.items())} if total else {},
        "reasons": dict(reasons.most_common()),
        "examples": {k: v for k, v in sorted(examples.items())},
    }


def _corpus_rule_sentences() -> list[tuple[str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for line in audit_lines(AUDIT / "real_facts.jsonl"):
        fact = json.loads(line)
        if fact["fact_type"] != "procedure_rule":
            continue
        text = (fact["value"].get("rule_text") or fact.get("excerpt") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append((DOCUMENT_KEYS.get(fact["source_id"], fact["source_id"]), text))
    return out


def _third_party_sentences() -> list[tuple[str, str]]:
    manifest = json.loads((REAL_FIXTURES / "MANIFEST.json").read_text())
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in manifest["documents"]:
        layout = layout_for((REAL_FIXTURES / entry["filename"]).read_bytes(), "application/pdf")
        for block in layout.included_blocks():
            for sentence in split_sentences(block.text):
                if not MODAL.search(sentence) or len(sentence) < 25 or sentence in seen:
                    continue
                seen.add(sentence)
                out.append((entry["filename"], sentence))
    return out


def main() -> int:
    corpus = _corpus_rule_sentences()
    third_party = _third_party_sentences()
    payload = {
        "question": "What fraction of real policy sentences yields an actor, a communication act and a governed object?",
        "measures": "coverage and the reasons for refusal",
        "does_not_measure": (
            "accuracy. Whether a located actor is the right actor still needs a reviewer. Unlike every other "
            "real-document question here the evidence is the sentence itself, and the sentence is present."
        ),
        "selection_bias": (
            "The corpus sample is sentences an earlier parser chose to emit, not a random sample of the "
            "documents, so coverage on a full document may differ in either direction."
        ),
        "samples": [
            _score(corpus, "real_corpus_rule_sentences",
                   "verbatim rule_text the previous parser read out of the retrieved documents"),
            _score(third_party, "real_third_party_document",
                   "every modal-bearing sentence in the committed FBI NIBRS data dictionary; out of domain by design"),
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "decomposition_coverage.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for sample in payload["samples"]:
        print(f"\n{sample['label']}: {sample['sentences']} sentences, "
              f"coverage {sample['coverage']} ({sample['fully_decomposed']} fully decomposed)")
        for name, stats in sample["elements_located"].items():
            print(f"    located {name:7s} {stats['n']:4d}  {stats['rate']:.3f}")
        for reason, count in sample["reasons"].items():
            print(f"    {reason:38s} {count:4d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
