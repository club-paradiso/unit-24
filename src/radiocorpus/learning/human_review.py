"""Human review decisions for the CHP learning content.

A human reviewer compares entries with the CHP 254 card itself and records one decision per
entry in ``data/adjudication/human/chp_reviews.jsonl``. This is the only way an entry becomes
human-verified, and the only way an entry the extractor misread can be taught: the reviewer
types the meaning as printed. Nothing here infers a meaning; it validates what a person wrote.

Record (one JSON object per line, schema ``human-review-1``)::

    {"schema": "human-review-1", "fact_id": "fct_…", "document_sha256": "<64 hex>",
     "decision": "ACCEPT" | "REJECT" | "CORRECT", "meaning_as_printed": null | "…",
     "page": 1, "reviewer": "name", "reviewed_at": "YYYY-MM-DD", "notes": ""}

* ``ACCEPT`` — the entry's shown answer matches the card. Only valid for a taught entry.
* ``REJECT`` — the entry should not be taught. ``notes`` must say why.
* ``CORRECT`` — ``meaning_as_printed`` is what the card says. If that text is not in the
  recorded excerpt, ``notes`` must say where on the card it was read.

The file is append-only. A later line from the same reviewer for the same fact replaces that
reviewer's earlier line. Different reviewers must agree; if they do not, the entry is marked
as disputed and is not human-verified.

An optional ``data/adjudication/human/chp_source_review.json`` (schema
``human-source-review-1``) records the card's printed revision and where and when the issuer
was seen listing it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

REVIEWS = Path("data/adjudication/human/chp_reviews.jsonl")
SOURCE_REVIEW = Path("data/adjudication/human/chp_source_review.json")

REVIEW_SCHEMA = "human-review-1"
SOURCE_REVIEW_SCHEMA = "human-source-review-1"
DECISIONS = ("ACCEPT", "REJECT", "CORRECT")
REVIEW_KEYS = {"schema", "fact_id", "document_sha256", "decision", "meaning_as_printed", "page", "reviewer", "reviewed_at", "notes"}
SOURCE_REVIEW_KEYS = {
    "schema",
    "document_sha256",
    "printed_revision",
    "listed_at_url",
    "listed_checked_at",
    "reviewer",
    "reviewed_at",
    "notes",
}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class HumanReviewError(ValueError):
    pass


@dataclass(frozen=True)
class HumanReview:
    fact_id: str
    decision: str
    meaning_as_printed: str | None
    page: int
    reviewer: str
    reviewed_at: str
    notes: str

    def public(self) -> dict[str, Any]:
        return {"reviewer": self.reviewer, "reviewed_at": self.reviewed_at, "decision": self.decision, "notes": self.notes}


@dataclass(frozen=True)
class Resolution:
    """What the human reviews of one fact add up to."""

    reviews: tuple[HumanReview, ...]
    decision: str | None  # None when reviewers disagree
    meaning: str | None

    @property
    def disputed(self) -> bool:
        return self.decision is None


def _norm(s: str) -> str:
    return " ".join(s.split()).casefold()


def _date(value: Any, where: str) -> str:
    if not isinstance(value, str) or not DATE.fullmatch(value):
        raise HumanReviewError(f"{where}: date must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as e:
        raise HumanReviewError(f"{where}: {e}") from None
    if parsed > date.today():
        raise HumanReviewError(f"{where}: date {value} is in the future")
    return value


def _reviewer(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 100:
        raise HumanReviewError(f"{where}: reviewer must be a non-empty name of at most 100 characters")
    return value.strip()


def parse_review(record: Any, where: str, gold: dict[str, dict[str, Any]], sha256: str, page_count: int, teachable: set[str]) -> HumanReview:
    """Validates one record against the gold rows it refers to. Raises HumanReviewError."""
    if not isinstance(record, dict):
        raise HumanReviewError(f"{where}: not a JSON object")
    if set(record) != REVIEW_KEYS:
        missing, extra = sorted(REVIEW_KEYS - set(record)), sorted(set(record) - REVIEW_KEYS)
        raise HumanReviewError(f"{where}: keys must be exactly {sorted(REVIEW_KEYS)} (missing {missing}, unexpected {extra})")
    if record["schema"] != REVIEW_SCHEMA:
        raise HumanReviewError(f"{where}: schema must be {REVIEW_SCHEMA!r}")
    fact_id = record["fact_id"]
    g = gold.get(fact_id)
    if g is None:
        raise HumanReviewError(f"{where}: {fact_id!r} is not a CHP entry")
    if record["document_sha256"] != sha256:
        raise HumanReviewError(f"{where}: document_sha256 does not match the CHP 254 card ({sha256}); the review must be of that exact file")
    decision = record["decision"]
    if decision not in DECISIONS:
        raise HumanReviewError(f"{where}: decision must be one of {DECISIONS}")
    page = record["page"]
    if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= page_count:
        raise HumanReviewError(f"{where}: page must be a whole number from 1 to {page_count}")
    notes = record["notes"]
    if not isinstance(notes, str):
        raise HumanReviewError(f'{where}: notes must be a string (use "" for none)')
    notes = notes.strip()
    meaning = record["meaning_as_printed"]
    if decision == "CORRECT":
        if not isinstance(meaning, str) or not meaning.strip():
            raise HumanReviewError(f"{where}: CORRECT needs meaning_as_printed, typed from the card")
        meaning = " ".join(meaning.split())
        if g["expected_value"]["kind"] not in {"code_meaning", "phonetic_letter"}:
            raise HumanReviewError(f"{where}: {g['key']} is not a code or letter entry and cannot be corrected")
        if _norm(meaning) not in _norm(g["excerpt"]) and not notes:
            raise HumanReviewError(f"{where}: the corrected meaning is not in the recorded excerpt, so notes must say where on the card it was read")
    elif meaning is not None:
        raise HumanReviewError(f"{where}: meaning_as_printed must be null unless the decision is CORRECT")
    if decision == "ACCEPT" and fact_id not in teachable:
        raise HumanReviewError(
            f"{where}: {g['key']} is not taught (its extracted meaning was rejected and is not shown), so it cannot be accepted; "
            "use CORRECT with the meaning as printed"
        )
    if decision == "REJECT" and not notes:
        raise HumanReviewError(f"{where}: REJECT needs notes saying why")
    return HumanReview(
        fact_id=fact_id,
        decision=decision,
        meaning_as_printed=meaning,
        page=page,
        reviewer=_reviewer(record["reviewer"], where),
        reviewed_at=_date(record["reviewed_at"], where),
        notes=notes,
    )


def load_reviews(path: Path, gold: dict[str, dict[str, Any]], sha256: str, page_count: int, teachable: set[str]) -> dict[str, Resolution]:
    """Reads and resolves every review. A missing file means no reviews."""
    if not path.exists():
        return {}
    latest: dict[tuple[str, str], HumanReview] = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{path.name} line {n}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            raise HumanReviewError(f"{where}: not valid JSON ({e.msg})") from None
        review = parse_review(record, where, gold, sha256, page_count, teachable)
        latest[(review.fact_id, review.reviewer.casefold())] = review
    by_fact: dict[str, list[HumanReview]] = {}
    for review in latest.values():
        by_fact.setdefault(review.fact_id, []).append(review)
    out: dict[str, Resolution] = {}
    for fact_id, reviews in by_fact.items():
        reviews.sort(key=lambda r: (r.reviewed_at, r.reviewer.casefold()))
        decisions = {r.decision for r in reviews}
        meanings = {_norm(r.meaning_as_printed) for r in reviews if r.meaning_as_printed}
        agreed = len(decisions) == 1 and len(meanings) <= 1
        decision = reviews[0].decision if agreed else None
        meaning = reviews[-1].meaning_as_printed if agreed and decision == "CORRECT" else None
        out[fact_id] = Resolution(reviews=tuple(reviews), decision=decision, meaning=meaning)
    return out


def load_source_review(path: Path, sha256: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HumanReviewError(f"{path.name}: not valid JSON ({e.msg})") from None
    where = path.name
    if not isinstance(record, dict) or set(record) != SOURCE_REVIEW_KEYS:
        raise HumanReviewError(f"{where}: keys must be exactly {sorted(SOURCE_REVIEW_KEYS)}")
    if record["schema"] != SOURCE_REVIEW_SCHEMA:
        raise HumanReviewError(f"{where}: schema must be {SOURCE_REVIEW_SCHEMA!r}")
    if record["document_sha256"] != sha256:
        raise HumanReviewError(f"{where}: document_sha256 does not match the CHP 254 card")
    revision = record["printed_revision"]
    if revision is not None and (not isinstance(revision, str) or not revision.strip()):
        raise HumanReviewError(f"{where}: printed_revision must be null or the text printed on the card")
    url, checked = record["listed_at_url"], record["listed_checked_at"]
    if (url is None) != (checked is None):
        raise HumanReviewError(f"{where}: listed_at_url and listed_checked_at go together")
    if url is not None and (not isinstance(url, str) or not url.startswith("https://www.chp.ca.gov/")):
        raise HumanReviewError(f"{where}: listed_at_url must be a page on https://www.chp.ca.gov/")
    return {
        "printed_revision": revision.strip() if isinstance(revision, str) else None,
        "listed_at_url": url,
        "listed_checked_at": _date(checked, where) if checked is not None else None,
        "reviewer": _reviewer(record["reviewer"], where),
        "reviewed_at": _date(record["reviewed_at"], where),
        "notes": record["notes"] if isinstance(record["notes"], str) else "",
    }
