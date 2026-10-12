"""The learner content bundle is a faithful projection of the audit, and nothing more."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from radiocorpus.learning import build, check, render
from radiocorpus.learning.content import INPUTS, LESSONS, OUTPUT, LearningContentError

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bundle() -> dict:
    return build(ROOT)


def test_committed_bundle_matches_fresh_export() -> None:
    assert check(ROOT) == []
    assert (ROOT / OUTPUT).read_text(encoding="utf-8") == render(build(ROOT))


def test_counts_match_the_audit(bundle: dict) -> None:
    assert bundle["counts"] == {
        "reviewed": 85,
        "teachable": 50,
        "teachable_codes": 24,
        "teachable_letters": 26,
        "excluded": 35,
        "human_verified": 0,
    }


def test_only_source_matched_labels_are_teachable(bundle: dict) -> None:
    gold = {
        r["fact_id"]: r
        for r in map(json.loads, (ROOT / "data/evaluation/gold_labels.jsonl").read_text().splitlines())
        if r["document_key"] == "CHP_AURAL_BREVITY"
    }
    for item in bundle["items"]:
        g = gold[item["id"]]
        assert g["label"] in {"TRUE_FACT", "WRONG_NORMALIZATION"}
        assert g["original_flags"]["exact_meaning_supported"] is True
        expected = g["expected_value"].get("meaning") or g["expected_value"]["word"]
        assert item["answer"].casefold() == expected.casefold()
    for e in bundle["excluded"]:
        assert gold[e["fact_id"]]["label"] in {"FALSE_POSITIVE", "INSUFFICIENT_CONTEXT"}


def test_excluded_entries_never_carry_the_rejected_meaning(bundle: dict) -> None:
    for e in bundle["excluded"]:
        assert set(e) == {"fact_id", "kind", "term", "code_system", "label", "failure_class", "reason", "locator"}


def test_every_item_is_traceable(bundle: dict) -> None:
    src = bundle["source"]
    assert len(src["sha256"]) == 64 and src["url"].startswith("https://www.chp.ca.gov/")
    for item in bundle["items"]:
        assert item["source_id"] == src["source_id"]
        assert item["locator"] in {"p.1", "p.2"} and item["page"] in {1, 2}
        assert item["excerpt"] and item["answer"].casefold() in item["excerpt"].casefold()
        assert item["term"] in item["excerpt"]


def test_nothing_claims_verification_or_currentness(bundle: dict) -> None:
    for item in bundle["items"]:
        assert item["status"] == {
            "source_matched": True,
            "human_verified": False,
            "eligibility": "RESEARCH_ONLY",
            "currentness": "UNKNOWN",
            "learner_safe": False,
        }
        assert item["review"]["reviewer_is_human"] is False
        assert any("no human has verified" in lim for lim in item["limitations"])
    assert bundle["source"]["currentness"] != "OFFICIAL_CURRENT_CONFIRMED"


def test_card_alphabet_is_not_labelled_apco_or_nato(bundle: dict) -> None:
    letters = {i["term"]: i for i in bundle["items"] if i["kind"] == "letter"}
    assert sorted(letters) == [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    assert letters["Y"]["answer"] == "Yellow"
    assert {i["code_system"] for i in letters.values()} == {"CHP_CARD_ALPHABET"}
    for t in "AFMPR":
        assert letters[t]["notes"], f"conflict for {t} must be disclosed"


def test_lessons_cover_every_item_once(bundle: dict) -> None:
    ids = [i for lesson in bundle["lessons"] for i in lesson["item_ids"]]
    assert sorted(ids) == sorted(i["id"] for i in bundle["items"])


def _copy_inputs(tmp_path: Path) -> Path:
    for rel in INPUTS:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    return tmp_path


def test_lesson_referencing_an_excluded_term_fails(tmp_path: Path) -> None:
    root = _copy_inputs(tmp_path)
    spec = json.loads((root / LESSONS).read_text())
    spec["lessons"][0]["terms"].append("10-4")
    (root / LESSONS).write_text(json.dumps(spec))
    with pytest.raises(LearningContentError, match="10-4"):
        build(root)


def test_stale_bundle_is_reported(tmp_path: Path) -> None:
    root = _copy_inputs(tmp_path)
    assert check(root) and "missing" in check(root)[0]
    (root / OUTPUT).parent.mkdir(parents=True)
    (root / OUTPUT).write_text("{}")
    assert "stale" in check(root)[0]
