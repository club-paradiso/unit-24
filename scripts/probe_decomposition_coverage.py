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

**Every sentence is recorded, not a sample of them.** An earlier version of this script kept
three examples per refusal reason, which was enough to state a headline number and not enough
for anyone to check it or to work from it. A coverage figure whose cases are not in the
repository cannot be audited, and cannot be compared against after a repair.

What this measures and what it does not: coverage, and the reason each sentence was refused.
Not accuracy. Whether a located actor is the *right* actor is a judgement, and judgements are
kept in ``decomposition_refusal_review.json`` — a separate file, marked as non-human review,
joined here but never folded into the mechanical counts. Selection bias is real and stated:
these are sentences an earlier parser chose to emit, not a random sample of the documents.

    uv run python scripts/probe_decomposition_coverage.py
"""

from __future__ import annotations

import collections
import hashlib
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
REVIEW = OUT / "decomposition_refusal_review.json"

#: Evidence heads that name why a sentence was refused, as opposed to describing what was done
#: on the way. The first one present is the reason.
REFUSAL_REASONS = frozenset({
    "no_modal", "no_subject_before_modal", "subject_too_long", "second_modal_inside_subject",
    "subject_is_a_date_label", "no_communication_verb_after_modal", "nearer_non_communication_verb",
    "communication_verb_too_far_from_modal", "no_noun_phrase_after_verb", "no_recipient_after_to",
    "recipient_after_to_without_message", "content_marker_without_object", "ambiguous_of_phrase",
})


def _reason(decomposition) -> str:
    """The first evidence line that explains a refusal, or ``complete``."""
    if decomposition.complete:
        return "complete"
    for note in decomposition.evidence:
        head = note.split(":", 1)[0]
        if head in REFUSAL_REASONS:
            return head
    missing = [
        name for name, value in (
            ("actor", decomposition.actor),
            ("action", decomposition.communication_action),
            ("object", decomposition.governed_object),
        ) if value is None
    ]
    return "missing:" + "+".join(missing) if missing else "incomplete_unclassified"


def _record(origin: str, sentence: str, reviews: dict) -> dict:
    """One sentence, what the decomposition made of it, and the review of that — joined, not merged."""
    d = decompose(sentence)
    digest = hashlib.sha256(sentence.encode()).hexdigest()
    review = reviews.get(digest)
    return {
        "sha256": digest,
        "origin": origin,
        "in_validation_set": origin in set(DOCUMENT_KEYS.values()),
        "sentence": sentence,
        "reason": _reason(d),
        "complete": d.complete,
        "actor": d.actor.to_dict() if d.actor else None,
        "communication_action": d.communication_action.to_dict() if d.communication_action else None,
        "governed_object": d.governed_object.to_dict() if d.governed_object else None,
        "recipient": d.recipient.to_dict() if d.recipient else None,
        "evidence": list(d.evidence),
        "review": (
            {"classification": review["classification"], "causes": review["causes"], "note": review["note"]}
            if review else None
        ),
    }


def _score(sentences: list[tuple[str, str]], label: str, note: str, reviews: dict) -> dict:
    records = [_record(origin, sentence, reviews) for origin, sentence in sentences]
    total = len(records)
    reasons: collections.Counter[str] = collections.Counter(r["reason"] for r in records)
    located: collections.Counter[str] = collections.Counter()
    for r in records:
        for name in ("actor", "communication_action", "governed_object"):
            if r[name] is not None:
                located[name] += 1

    by_source: dict[str, dict] = {}
    for r in records:
        bucket = by_source.setdefault(
            r["origin"], {"sentences": 0, "fully_decomposed": 0, "in_validation_set": r["in_validation_set"]}
        )
        bucket["sentences"] += 1
        bucket["fully_decomposed"] += int(r["complete"])
    for bucket in by_source.values():
        bucket["coverage"] = round(bucket["fully_decomposed"] / bucket["sentences"], 4)

    validation = [r for r in records if r["in_validation_set"]]
    reviewed = [r for r in records if r["review"]]
    classifications = collections.Counter(r["review"]["classification"] for r in reviewed)
    causes: collections.Counter[str] = collections.Counter()
    for r in reviewed:
        causes.update(r["review"]["causes"])

    return {
        "label": label,
        "note": note,
        "sentences": total,
        "fully_decomposed": reasons["complete"],
        "coverage": round(reasons["complete"] / total, 4) if total else None,
        # The same measurement over the layout-validation documents alone. Membership is
        # structural — the source appears in DOCUMENT_KEYS — not a hand-listed set of agencies.
        "validation_documents_only": {
            "sentences": len(validation),
            "fully_decomposed": sum(1 for r in validation if r["complete"]),
            "coverage": round(sum(1 for r in validation if r["complete"]) / len(validation), 4) if validation else None,
        },
        "elements_located": {
            k: {"n": v, "rate": round(v / total, 4)} for k, v in sorted(located.items())
        } if total else {},
        "reasons": dict(reasons.most_common()),
        "by_source": dict(sorted(by_source.items(), key=lambda kv: (-kv[1]["sentences"], kv[0]))),
        "review_rollup": {
            "reviewed": len(reviewed),
            "unreviewed": total - len(reviewed),
            "classifications": dict(classifications.most_common()),
            "causes": dict(causes.most_common()),
        },
        "records": records,
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
    reviews = json.loads(REVIEW.read_text())["reviews"] if REVIEW.exists() else {}
    corpus = _corpus_rule_sentences()
    third_party = _third_party_sentences()
    samples = [
        _score(corpus, "real_corpus_rule_sentences",
               "verbatim rule_text the previous parser read out of the retrieved documents", reviews),
        _score(third_party, "real_third_party_document",
               "every modal-bearing sentence in the committed FBI NIBRS data dictionary; out of domain by design",
               reviews),
    ]
    present = {r["sha256"] for s in samples for r in s["records"]}
    payload = {
        "question": "What fraction of real policy sentences yields an actor, a communication act and a governed object?",
        "measures": "coverage, and the reason each sentence was refused",
        "does_not_measure": (
            "accuracy. Whether a located actor is the right actor is a judgement and lives in "
            "decomposition_refusal_review.json, joined into each record but never counted here."
        ),
        "completeness": "every sentence in both samples is recorded, not a sample of them",
        "selection_bias": (
            "The corpus sample is sentences an earlier parser chose to emit, not a random sample of the "
            "documents, so coverage on a full document may differ in either direction. Two of its six "
            "sources are not radio-communication documents at all, which the per-source rollup shows."
        ),
        "review_integrity": {
            "review_file": REVIEW.name,
            "stale_reviews": sorted(set(reviews) - present),
            "unreviewed_sentences": sorted(present - set(reviews)),
        },
        "samples": samples,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "decomposition_coverage.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )

    for sample in samples:
        v = sample["validation_documents_only"]
        print(f"\n{sample['label']}: {sample['sentences']} sentences, "
              f"coverage {sample['coverage']} ({sample['fully_decomposed']} fully decomposed)")
        if v["sentences"]:
            print(f"    validation documents only: {v['fully_decomposed']}/{v['sentences']} = {v['coverage']}")
        for name, stats in sample["elements_located"].items():
            print(f"    located {name:22s} {stats['n']:4d}  {stats['rate']:.3f}")
        for source, stats in sample["by_source"].items():
            print(f"    {source:26s} {stats['fully_decomposed']:3d}/{stats['sentences']:<3d} {stats['coverage']:.3f}")
        for reason, count in sample["reasons"].items():
            print(f"    {reason:38s} {count:4d}")
        rollup = sample["review_rollup"]
        print(f"    reviewed {rollup['reviewed']}/{sample['sentences']}: {rollup['classifications']}")

    integrity = payload["review_integrity"]
    if integrity["stale_reviews"] or integrity["unreviewed_sentences"]:
        print(f"\nreview integrity: {len(integrity['stale_reviews'])} stale, "
              f"{len(integrity['unreviewed_sentences'])} unreviewed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
