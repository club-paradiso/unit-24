"""Build the learner-facing CHP content bundle from committed audit evidence.

Nothing here reads a document or infers a meaning. The bundle is a projection of what the
independent source review (``data/audit/fact_audit.jsonl``, restated in
``data/evaluation/gold_labels.jsonl``) already decided:

* a code is teachable only when the review found meaning, normalisation and scope all correct
  (gold label ``TRUE_FACT``);
* a phonetic letter is teachable when the review found the word itself supported and the only
  defect is the claimed alphabet system (gold label ``WRONG_NORMALIZATION``). The system claim is
  dropped, not repaired: the bundle calls it the card's own alphabet;
* everything else is listed as excluded with the review's reason and *without* the extracted
  meaning, because that meaning is what the review found wrong.

No teachable item is learner-safe in the corpus sense. That determination is human-only
(``tests/test_adjudication.py``), and no human has made it, so every item carries
``human_verified: false``, ``eligibility: RESEARCH_ONLY`` and ``currentness: UNKNOWN``.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from radiocorpus.learning.human_review import REVIEWS, SOURCE_REVIEW, HumanReviewError, Resolution, load_reviews, load_source_review

SCHEMA_VERSION = 2
DOCUMENT_KEY = "CHP_AURAL_BREVITY"
SOURCE_ID = "src_29af34430672001d"
AGENCY_ID = "CAN-S05"

GOLD = Path("data/evaluation/gold_labels.jsonl")
AUDIT = Path("data/audit/fact_audit.jsonl")
SOURCES = Path("data/audit/real_sources.jsonl")
CONFLICTS = Path("data/audit/real_conflicts.jsonl")
MANIFEST = Path("data/raw/layout-validation/MANIFEST.json")
LESSONS = Path("data/learning/chp_lessons.json")
OUTPUT = Path("web/src/content/chp.json")

INPUTS = [GOLD, AUDIT, SOURCES, CONFLICTS, MANIFEST, LESSONS, REVIEWS]
OPTIONAL_INPUTS = [SOURCE_REVIEW]

NEW_LESSON = {
    "id": "newly-reviewed",
    "title": "Newly reviewed entries",
    "summary": "Entries a human reviewer read from the card after they were first left out.",
    "title_ko": "새로 검수된 항목",
    "summary_ko": "처음에는 빠졌다가 사람 검수자가 카드에서 직접 읽어 추가한 항목",
}
LESSON_FIELDS = ("id", "title", "summary", "title_ko", "summary_ko")

ALPHABET_SYSTEM = "CHP_CARD_ALPHABET"

COMMON_LIMITATIONS = [
    "Matched to the source by an automated (AI agent) review on 2026-09-20; no human has verified it.",
    "Whether the card is still in use is unknown: it carries no confirmed revision or effective date.",
    "Applies to the California Highway Patrol card only; other agencies may use the same code differently.",
]
CODE_LIMITATIONS = ["The card gives the meaning only; it gives no guidance on when or how the code is used on air."]
LETTER_LIMITATIONS = [
    "This is the card's own spelling alphabet. It is not the APCO 1941 alphabet (the card prints Y = Yellow, not Young) "
    "and not the NATO/ICAO alphabet."
]


class LearningContentError(ValueError):
    pass


def _who(res: Resolution) -> str:
    return "; ".join(f"{r.reviewer} ({r.reviewed_at})" for r in res.reviews)


def _human_limitation(res: Resolution | None) -> str:
    if res is None:
        return COMMON_LIMITATIONS[0]
    n = len(res.reviews)
    if res.disputed:
        return f"Human reviewers disagree about this entry ({_who(res)}); until they agree it is not human-verified."
    if res.decision == "CORRECT":
        return f"The extractor misread this entry; the meaning shown was read from the card by {n} human reviewer(s): {_who(res)}."
    return f"Matched to the card by an automated review on 2026-09-20 and verified by {n} human reviewer(s): {_who(res)}."


def _human_state(res: Resolution | None) -> str:
    if res is None:
        return "none"
    if res.disputed:
        return "disputed"
    return {"ACCEPT": "accepted", "CORRECT": "corrected", "REJECT": "rejected"}[res.decision or ""]


def _currentness_limitation(source_review: dict[str, Any] | None) -> str:
    if source_review and source_review["listed_at_url"]:
        return (
            f"CHP listed this card at {source_review['listed_at_url']} on {source_review['listed_checked_at']} "
            f"(checked by {source_review['reviewer']}). That shows it was published then, not that it is in operational use."
        )
    return COMMON_LIMITATIONS[1]


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _page(locator: str) -> int | None:
    m = re.fullmatch(r"p\.(\d+)", locator)
    return int(m.group(1)) if m else None


def _display_word(word: str, letter: str, excerpt: str) -> str:
    """The word as printed in the excerpt (``A Adam N Nora`` gives ``Adam``), else as recorded."""
    m = re.search(rf"(?:^|\s){re.escape(letter)}\s+({re.escape(word)})(?:\s|$)", excerpt, flags=re.IGNORECASE)
    return m.group(1) if m else word


SYSTEM_ORDER = {"TEN_CODE": 0, "ELEVEN_CODE": 1, ALPHABET_SYSTEM: 2}


def _order(entry: dict[str, Any]) -> tuple[Any, ...]:
    nums = [int(n) for n in re.findall(r"\d+", entry["term"])]
    return (entry["kind"] != "code", SYSTEM_ORDER.get(entry.get("code_system") or "", 3), nums, entry["term"])


def _review(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": audit["review_method"],
        "reviewer": audit["reviewer"],
        "reviewer_is_human": bool(audit["human_review"]),
        "reviewed_at": audit["reviewed_at"],
        "inspection": audit.get("inspection"),
        "finding": audit["reason"],
    }


def _status(audit: dict[str, Any], res: Resolution | None, source_review: dict[str, Any] | None) -> dict[str, Any]:
    currentness = "UNKNOWN" if audit["source_current"] == "not_confirmed" else audit["source_current"]
    if source_review and source_review["listed_checked_at"]:
        currentness = f"LISTED_BY_ISSUER_{source_review['listed_checked_at']}"
    return {
        "source_matched": True,
        "human_verified": res is not None and not res.disputed and res.decision in {"ACCEPT", "CORRECT"},
        "human_review": _human_state(res),
        "answer_basis": "human_reading" if res is not None and res.decision == "CORRECT" else "automated_review",
        "eligibility": audit["decision"],
        "currentness": currentness,
        "learner_safe": bool(audit["safe_expected_answer"]),
    }


def _source(root: Path, source_review: dict[str, Any] | None = None) -> dict[str, Any]:
    src = next(r for r in _jsonl(root / SOURCES) if r["source_id"] == SOURCE_ID)
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    doc = next(d for d in manifest["documents"] if d["key"] == DOCUMENT_KEY)
    if src["document_hash"] != f"sha256:{doc['expected_sha256']}":
        raise LearningContentError("source hash in real_sources.jsonl disagrees with the layout-validation manifest")
    printed = source_review["printed_revision"] if source_review else None
    return {
        "source_id": SOURCE_ID,
        "title": "CHP 254 — Aural Brevity Card",
        "title_basis": "Form number and name as given in the document's URL; the recorded source title is null.",
        "issuing_agency": doc["agency"],
        "jurisdiction": "California (state highway patrol)",
        "version": printed or "01-2021 v2",
        "version_basis": (
            f"As printed on the card, recorded by {source_review['reviewer']} on {source_review['reviewed_at']}."
            if printed and source_review
            else "Taken from the file name only. The card's printed revision and effective date were not confirmed."
        ),
        "url": src["canonical_url"],
        "sha256": doc["expected_sha256"],
        "byte_length": doc["expected_byte_length"],
        "page_count": doc["expected_page_count"],
        "retrieved_at": src["retrieved_at"],
        "currentness": src["currentness"],
        "source_quality": src["source_quality"],
        "document_in_repository": False,
        "document_note": "The PDF is a third-party document and is not committed; only its identity (hash, size, URL) is recorded.",
        "human_source_review": source_review,
    }


def _teachable(g: dict[str, Any], audit: dict[str, Any]) -> bool:
    """The automated review's verdict: was the extracted meaning found on the card exactly?"""
    kind = g["expected_value"]["kind"]
    if kind == "code_meaning":
        return g["label"] == "TRUE_FACT"
    return (
        kind == "phonetic_letter"
        and g["label"] == "WRONG_NORMALIZATION"
        and audit["exact_meaning_supported"]
        and audit["agency_attribution_correct"]
        and audit["locator_correct"]
    )


def build(root: Path) -> dict[str, Any]:
    gold = [r for r in _jsonl(root / GOLD) if r["document_key"] == DOCUMENT_KEY]
    audits = {r["fact_id"]: r for r in _jsonl(root / AUDIT)}
    conflicts = [c for c in _jsonl(root / CONFLICTS) if c["agency_id"] == AGENCY_ID]
    by_fact = {r["fact_id"]: r for r in gold}
    if not gold:
        raise LearningContentError(f"no gold labels for {DOCUMENT_KEY}")
    for g in gold:
        audit = audits.get(g["fact_id"])
        if audit is None:
            raise LearningContentError(f"{g['fact_id']} has a gold label but no audit record")
        if g["source_id"] != SOURCE_ID or audit["source_id"] != SOURCE_ID:
            raise LearningContentError(f"{g['fact_id']} cites a different source")
        if audit["human_review"]:
            raise LearningContentError(f"{g['fact_id']}: human review recorded in the audit; human decisions belong in {REVIEWS.as_posix()}")

    machine_teachable = {g["fact_id"] for g in gold if _teachable(g, audits[g["fact_id"]])}
    source = _source(root)
    try:
        resolutions = load_reviews(root / REVIEWS, by_fact, source["sha256"], source["page_count"], machine_teachable)
        source_review = load_source_review(root / SOURCE_REVIEW, source["sha256"])
    except HumanReviewError as e:
        raise LearningContentError(f"human review: {e}") from None
    source = _source(root, source_review)

    items: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    rejected_terms: set[str] = set()
    for g in gold:
        audit = audits[g["fact_id"]]
        res = resolutions.get(g["fact_id"])
        value = g["expected_value"]
        kind = value["kind"]
        term = value.get("code") or value.get("letter") or value.get("system")
        human = [r.public() for r in res.reviews] if res else []
        corrected = res is not None and not res.disputed and res.decision == "CORRECT"
        rejected = res is not None and not res.disputed and res.decision == "REJECT"
        teach = (g["fact_id"] in machine_teachable or corrected) and not rejected
        if not teach:
            entry = {
                "fact_id": g["fact_id"],
                "kind": "letter" if kind.startswith("phonetic") else "code",
                "term": term,
                "code_system": value.get("code_system"),
                "label": g["label"],
                "failure_class": g["failure_class"],
                "reason": g["rationale"],
                "locator": g["locator"],
                "page": _page(g["locator"]),
                # Raw extraction text, for reviewers. It is source text, not an answer: the app never
                # presents it as this entry's meaning.
                "excerpt": g["excerpt"],
                "human": human,
                "human_review": _human_state(res),
            }
            if rejected and g["fact_id"] in machine_teachable:
                rejected_terms.add(term)
                entry |= {"label": "HUMAN_REJECTED", "failure_class": "HUMAN_REVIEW", "reason": f"Rejected by human review: {_who(res)}"}
            excluded.append(entry)
            continue
        item: dict[str, Any] = {
            "id": g["fact_id"],
            "locator": g["locator"],
            "page": _page(g["locator"]),
            "locator_kind": audit["locator_kind"],
            "excerpt": g["excerpt"],
            "source_id": SOURCE_ID,
            "review": _review(audit) | {"human": human},
            "status": _status(audit, res, source_review),
            "notes": [],
        }
        limitations = [_human_limitation(res), _currentness_limitation(source_review), COMMON_LIMITATIONS[2]]
        if corrected:
            assert res is not None and res.meaning is not None
            item["notes"].append(
                "The excerpt is the extractor's text from this part of the card, kept for reference; it may run into neighbouring columns."
            )
        if kind == "code_meaning":
            item |= {
                "kind": "code",
                "code_system": value["code_system"],
                "term": value["code"],
                "answer": res.meaning if corrected and res else value["meaning"],
                "limitations": limitations + CODE_LIMITATIONS,
            }
        else:
            item |= {
                "kind": "letter",
                "code_system": ALPHABET_SYSTEM,
                "term": value["letter"],
                "answer": res.meaning if corrected and res else _display_word(value["word"], value["letter"], g["excerpt"]),
                "limitations": limitations + LETTER_LIMITATIONS,
            }
        items.append(item)

    seen: dict[str, str] = {}
    for i in items:
        if i["term"] in seen:
            raise LearningContentError(f"two teachable entries share the term {i['term']} ({seen[i['term']]}, {i['id']})")
        seen[i["term"]] = i["id"]
    by_term = seen

    by_id = {i["id"]: i for i in items}
    for c in conflicts:
        winners = [f for f in c["fact_ids"] if f in by_id]
        losers = [by_fact[f] for f in c["fact_ids"] if f not in by_id and f in by_fact]
        if any(f in resolutions for f in c["fact_ids"]):
            continue  # a human has ruled on this letter; their decision is shown instead of the machine note
        if len(winners) != 1 or not losers:
            raise LearningContentError(f"conflict {c['conflict_id']} does not separate into one teachable and rejected rest")
        for lost in losers:
            word = lost["expected_value"].get("word")
            by_id[winners[0]]["notes"].append(
                f"The extractor also read '{word}' for this letter elsewhere on the card. The review rejected that reading "
                f"({lost['rationale'].split(';')[0]}). The corpus still records this as an unresolved conflict ({c['conflict_id']})."
            )

    spec = json.loads((root / LESSONS).read_text(encoding="utf-8"))
    lessons = []
    for lesson in spec["lessons"]:
        missing = [t for t in lesson["terms"] if t not in by_term and t not in rejected_terms]
        if missing:
            raise LearningContentError(f"lesson {lesson['id']} references non-teachable terms: {missing}")
        ids = [by_term[t] for t in lesson["terms"] if t in by_term]
        if ids:
            lessons.append({k: lesson[k] for k in LESSON_FIELDS} | {"item_ids": ids})
    in_lessons = {i for lesson in lessons for i in lesson["item_ids"]}
    leftover = [i for i in sorted(items, key=_order) if i["id"] not in in_lessons]
    unreviewed = [i["id"] for i in leftover if i["status"]["answer_basis"] != "human_reading"]
    if unreviewed:
        raise LearningContentError(f"teachable items missing from every lesson: {unreviewed}")
    if leftover:
        lessons.append(NEW_LESSON | {"item_ids": [i["id"] for i in leftover]})

    items.sort(key=_order)
    excluded.sort(key=lambda e: (*_order(e), e["fact_id"]))
    body = {
        "schema_version": SCHEMA_VERSION,
        "jurisdiction": {
            "id": "chp",
            "name": "California Highway Patrol",
            "short_name": "CHP",
            "region": "California, USA",
            "agency_id": AGENCY_ID,
        },
        "source": source,
        "counts": {
            "reviewed": len(gold),
            "teachable": len(items),
            "teachable_codes": sum(i["kind"] == "code" for i in items),
            "teachable_letters": sum(i["kind"] == "letter" for i in items),
            "excluded": len(excluded),
            "human_verified": sum(i["status"]["human_verified"] for i in items),
            "human_corrected": sum(i["status"]["human_review"] == "corrected" for i in items),
            "human_rejected": sum(e["label"] == "HUMAN_REJECTED" for e in excluded),
            "human_disputed": sum(1 for r in resolutions.values() if r.disputed),
            "human_reviewers": len({r.reviewer.casefold() for res in resolutions.values() for r in res.reviews}),
        },
        "generated_from": [p.as_posix() for p in INPUTS + [x for x in OPTIONAL_INPUTS if (root / x).exists()]],
        "lessons": lessons,
        "items": items,
        "excluded": excluded,
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return {"content_version": digest} | body


def render(bundle: dict[str, Any]) -> str:
    return json.dumps(bundle, indent=2, ensure_ascii=False) + "\n"


def export(root: Path, out: Path | None = None) -> Path:
    target = root / (out or OUTPUT)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(build(root)), encoding="utf-8")
    return target


def check(root: Path) -> list[str]:
    """Violations if the committed bundle is missing or differs from a fresh build."""
    target = root / OUTPUT
    if not target.exists():
        return [f"{OUTPUT.as_posix()} is missing; run `radiocorpus export-learning`"]
    try:
        fresh = render(build(root))
    except LearningContentError as e:
        return [str(e)]
    if target.read_text(encoding="utf-8") != fresh:
        return [f"{OUTPUT.as_posix()} is stale; run `radiocorpus export-learning`"]
    return []
