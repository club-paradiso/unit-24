"""Human review decisions change the learner bundle exactly as documented, and nothing else does."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from radiocorpus.learning import build
from radiocorpus.learning.content import INPUTS, LearningContentError
from radiocorpus.learning.human_review import REVIEWS, SOURCE_REVIEW

ROOT = Path(__file__).resolve().parents[1]
SHA = "eec212ac94b0f12cbfbf5286cde85995e96e83d66f40939aa9c3d3406c1e6064"


def fid(key: str) -> str:
    rows = [r for r in map(json.loads, (ROOT / "data/evaluation/gold_labels.jsonl").read_text().splitlines()) if r["key"] == key]
    rows = [r for r in rows if r["document_key"] == "CHP_AURAL_BREVITY"]
    # letter:A has two rows (Adam taught, Armed rejected); prefer the taught one.
    rows.sort(key=lambda r: r["label"] not in {"TRUE_FACT", "WRONG_NORMALIZATION"})
    return rows[0]["fact_id"]


def review(key: str, decision: str, meaning: str | None = None, reviewer: str = "A. Reviewer", notes: str = "", page: int = 1, **over) -> dict:
    return {
        "schema": "human-review-1",
        "fact_id": fid(key),
        "document_sha256": SHA,
        "decision": decision,
        "meaning_as_printed": meaning,
        "page": page,
        "reviewer": reviewer,
        "reviewed_at": "2026-10-13",
        "notes": notes,
    } | over


@pytest.fixture
def root(tmp_path: Path) -> Path:
    for rel in INPUTS:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    return tmp_path


def write(root: Path, *records: dict) -> dict:
    (root / REVIEWS).write_text("".join(json.dumps(r) + "\n" for r in records))
    return build(root)


def item(bundle: dict, term: str) -> dict | None:
    return next((i for i in bundle["items"] if i["term"] == term), None)


def excluded(bundle: dict, term: str) -> list[dict]:
    return [e for e in bundle["excluded"] if e["term"] == term]


def test_empty_file_changes_nothing(root: Path) -> None:
    assert write(root) == build(ROOT)


def test_accept_marks_an_entry_human_verified(root: Path) -> None:
    b = write(root, review("10-1", "ACCEPT"))
    it = item(b, "10-1")
    assert it["status"]["human_verified"] is True and it["status"]["human_review"] == "accepted"
    assert it["review"]["human"] == [{"reviewer": "A. Reviewer", "reviewed_at": "2026-10-13", "decision": "ACCEPT", "notes": ""}]
    assert it["limitations"][0].startswith("Matched to the card by an automated review on 2026-09-20 and verified by 1 human reviewer(s)")
    assert b["counts"]["human_verified"] == 1 and b["counts"]["human_reviewers"] == 1
    # The corpus eligibility is untouched: human review is reported, not promoted into the policy.
    assert it["status"]["eligibility"] == "RESEARCH_ONLY"
    assert item(b, "10-2")["status"]["human_verified"] is False


def test_reject_moves_a_taught_entry_out_and_out_of_its_lesson(root: Path) -> None:
    b = write(root, review("10-1", "REJECT", notes="Card shows a different meaning"))
    assert item(b, "10-1") is None
    [e] = excluded(b, "10-1")
    assert e["label"] == "HUMAN_REJECTED" and "A. Reviewer" in e["reason"]
    assert all(fid("10-1") not in lesson["item_ids"] for lesson in b["lessons"])
    assert b["counts"]["teachable"] == 49 and b["counts"]["human_rejected"] == 1


def test_correct_teaches_an_excluded_entry_with_the_human_reading(root: Path) -> None:
    b = write(root, review("10-4", "CORRECT", "Message received"))
    it = item(b, "10-4")
    assert it["answer"] == "Message received"
    assert it["status"] | {} == it["status"] and it["status"]["answer_basis"] == "human_reading"
    assert it["status"]["human_verified"] is True and it["status"]["human_review"] == "corrected"
    assert it["review"]["finding"] == "Armed belongs to adjacent 10-36A"  # the automated review's own words, unchanged
    assert "read from the card" in it["limitations"][0]
    assert not excluded(b, "10-4")
    assert b["lessons"][-1]["id"] == "newly-reviewed" and b["lessons"][-1]["item_ids"] == [it["id"]]
    assert b["counts"]["teachable"] == 51


def test_correct_can_replace_a_taught_answer(root: Path) -> None:
    b = write(root, review("10-1", "CORRECT", "Reception poor", notes=""))
    assert item(b, "10-1")["status"]["human_review"] == "corrected"
    assert b["lessons"][0]["item_ids"][0] == fid("10-1")


def test_reviewers_who_disagree_verify_nothing(root: Path) -> None:
    b = write(root, review("10-1", "ACCEPT"), review("10-1", "REJECT", reviewer="B. Second", notes="disagree"))
    it = item(b, "10-1")
    assert it["status"]["human_verified"] is False and it["status"]["human_review"] == "disputed"
    assert it["limitations"][0].startswith("Human reviewers disagree")
    assert b["counts"]["human_disputed"] == 1


def test_a_reviewers_later_line_replaces_their_earlier_one(root: Path) -> None:
    b = write(root, review("10-1", "REJECT", notes="misread"), review("10-1", "ACCEPT"))
    assert item(b, "10-1")["status"]["human_review"] == "accepted"


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (review("10-1", "ACCEPT", document_sha256="0" * 64), "document_sha256"),
        (review("10-1", "ACCEPT", fact_id="fct_nope"), "not a CHP entry"),
        (review("10-4", "CORRECT"), "needs meaning_as_printed"),
        (review("10-4", "ACCEPT"), "cannot be accepted"),
        (review("10-1", "REJECT"), "needs notes"),
        (review("10-1", "ACCEPT", meaning_as_printed="x"), "must be null"),
        (review("10-1", "ACCEPT", reviewer=" "), "reviewer"),
        (review("10-1", "ACCEPT", reviewed_at="13/10/2026"), "YYYY-MM-DD"),
        (review("10-1", "ACCEPT", reviewed_at="2999-01-01"), "future"),
        (review("10-1", "ACCEPT", page=3), "page"),
        (review("10-1", "MAYBE"), "decision"),
        (review("10-4", "CORRECT", "Something not on the card"), "notes must say where"),
        ({"schema": "human-review-1"}, "keys must be exactly"),
    ],
)
def test_invalid_records_fail_the_build(root: Path, record: dict, message: str) -> None:
    with pytest.raises(LearningContentError, match=message):
        write(root, record)


def test_a_correction_off_the_excerpt_is_allowed_with_a_location(root: Path) -> None:
    b = write(
        root, review("10-36P", "CORRECT", "Confidential information, subject possibly on parole, probation", notes="Second line of the cell, page 1")
    )
    assert item(b, "10-36P")["answer"].startswith("Confidential information, subject possibly on parole")


def test_two_entries_cannot_teach_the_same_letter(root: Path) -> None:
    armed = next(
        r["fact_id"]
        for r in map(json.loads, (ROOT / "data/evaluation/gold_labels.jsonl").read_text().splitlines())
        if r["key"] == "letter:A" and r["label"] == "FALSE_POSITIVE"
    )
    with pytest.raises(LearningContentError, match="share the term A"):
        write(root, review("10-1", "CORRECT", "Armed", fact_id=armed, page=2))


def test_source_review_sets_printed_revision_and_listing(root: Path) -> None:
    (root / SOURCE_REVIEW).write_text(
        json.dumps(
            {
                "schema": "human-source-review-1",
                "document_sha256": SHA,
                "printed_revision": "CHP 254 (Rev. 01-21)",
                "listed_at_url": "https://www.chp.ca.gov/forms",
                "listed_checked_at": "2026-10-13",
                "reviewer": "A. Reviewer",
                "reviewed_at": "2026-10-13",
                "notes": "",
            }
        )
    )
    b = write(root)
    assert b["source"]["version"] == "CHP 254 (Rev. 01-21)"
    assert b["source"]["version_basis"].startswith("As printed on the card")
    assert item(b, "10-1")["status"]["currentness"] == "LISTED_BY_ISSUER_2026-10-13"
    assert "not that it is in operational use" in item(b, "10-1")["limitations"][1]
    assert "data/adjudication/human/chp_source_review.json" in b["generated_from"]


def test_source_review_rejects_off_site_evidence(root: Path) -> None:
    (root / SOURCE_REVIEW).write_text(
        json.dumps(
            {
                "schema": "human-source-review-1",
                "document_sha256": SHA,
                "printed_revision": None,
                "listed_at_url": "https://example.com/chp-codes",
                "listed_checked_at": "2026-10-13",
                "reviewer": "A",
                "reviewed_at": "2026-10-13",
                "notes": "",
            }
        )
    )
    with pytest.raises(LearningContentError, match="chp.ca.gov"):
        write(root)


def test_web_review_fixture_is_valid_input(root: Path) -> None:
    """The reviewer page's exporter output (shared fixture) is accepted by the Python validator."""
    fixture = ROOT / "web/src/review/fixture.jsonl"
    shutil.copy(fixture, root / REVIEWS)
    b = build(root)
    assert b["counts"]["human_reviewers"] == 1
