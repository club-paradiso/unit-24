"""Tests for the adjudication instrument.

The instrument's whole job is to stop a number being reported that nobody earned. Most of
these tests assert a refusal rather than a result.
"""

from __future__ import annotations

import json
from pathlib import Path

from radiocorpus.evaluation.adjudication import (
    AdjudicationRecord,
    Currentness,
    MissedFact,
    Verdict,
    claim_is_carried,
    mark_absent_claims,
    read_records,
    score,
    seed_from_audit,
    write_records,
)
from radiocorpus.evaluation.gold import DOCUMENT_KEYS, audit_lines

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "audit"
WORKSHEET = ROOT / "data" / "adjudication" / "real_document_worksheet.jsonl"


def _procedure(**overrides) -> AdjudicationRecord:
    record = AdjudicationRecord(
        adjudication_id="adj_t",
        document_key="DOC",
        document_sha256=None,
        family="procedure_rule",
        candidate_id="proc:acknowledgement",
        locator="p.1",
        excerpt="Members will acknowledge the transmission.",
        parser_value={"procedure": "acknowledgement", "rule_text": "..."},
    )
    for key, value in overrides.items():
        setattr(record, key, value)
    return record


# ---------------------------------------------------------------- a blank is never a pass


def test_unadjudicated_blocks_the_metric_rather_than_counting_as_correct():
    """The failure this instrument exists to prevent: a blank read as agreement."""
    record = _procedure(meaning_supported=Verdict.SUPPORTED)
    result = score([record])["per_family"]["procedure_rule"]
    assert result["candidate_meaning"]["precision"] == 1.0
    assert result["complete_fact"]["precision"] is None
    assert result["complete_fact"]["unadjudicated"] == 1
    assert "unadjudicated" in result["complete_fact"]["blocked_reason"]


def test_recall_is_null_without_an_inventory_of_what_the_document_contains():
    record = _procedure(meaning_supported=Verdict.SUPPORTED)
    recall = score([record])["per_family"]["procedure_rule"]["recall"]
    assert recall["recall"] is None
    assert "cannot evidence what was missed" in recall["blocked_reason"]


def test_recall_is_computed_only_against_a_reviewer_supplied_inventory():
    record = _procedure(meaning_supported=Verdict.SUPPORTED)
    missed = [MissedFact("DOC", "procedure_rule", "proc:relay", "...", "p.2", "reviewer")]
    recall = score([record], missed)["per_family"]["procedure_rule"]["recall"]
    assert recall == {"tp": 1, "fn": 1, "recall": 0.5, "source": "reviewer-supplied missed-fact inventory"}


# ---------------------------------------------------------------- claims never made


def test_a_claim_the_candidate_never_made_is_missing_not_unadjudicated():
    """Absence is a fact about the candidate, so it needs no document to decide.

    The distinction is the whole reason both verdicts exist: MISSING says the candidate is
    silent, UNADJUDICATED says the reviewer is.
    """
    record = _procedure()
    assert not claim_is_carried(record, "procedure_actor")
    decided = mark_absent_claims(record)
    assert "procedure_actor" in decided
    assert record.procedure_actor == Verdict.MISSING
    assert record.mechanical_rule.startswith("claim_absent_from_candidate")


def test_a_claim_present_but_false_is_still_a_claim():
    """`has_condition: false` asserts that no condition governs the rule. That is judgeable."""
    record = _procedure(parser_value={"procedure": "x", "has_condition": False})
    assert claim_is_carried(record, "condition_correct")
    assert "condition_correct" not in mark_absent_claims(record)
    assert record.condition_correct == Verdict.UNADJUDICATED


def test_a_claim_present_but_null_carries_nothing():
    record = _procedure(parser_value={"procedure": "x", "section_heading": None})
    assert not claim_is_carried(record, "section_scope_correct")
    assert "section_scope_correct" in mark_absent_claims(record)


def test_absence_never_overwrites_a_reviewer_verdict():
    """A reviewer's judgement outranks a mechanical one, always."""
    record = _procedure(section_scope_correct=Verdict.WRONG)
    mark_absent_claims(record)
    assert record.section_scope_correct == Verdict.WRONG
    assert "section_scope_correct" not in record.mechanically_decided


def test_learner_safety_can_never_be_decided_mechanically():
    """Whether a fact is safe to put in front of a learner is a judgement, not a shape.

    It has no carrier key, so the absence pass cannot reach it, and a record stays
    unadjudicated until somebody decides it.
    """
    record = _procedure(meaning_supported=Verdict.SUPPORTED)
    mark_absent_claims(record)
    assert record.learner_safe_in_principle == Verdict.UNADJUDICATED
    assert "learner_safe_in_principle" in record.unadjudicated_fields()


def test_a_missing_claim_cannot_make_a_complete_fact():
    record = _procedure(
        meaning_supported=Verdict.SUPPORTED,
        agency_correct=Verdict.SUPPORTED,
        region_correct=Verdict.SUPPORTED,
        learner_safe_in_principle=Verdict.SUPPORTED,
        currentness=Currentness.CURRENT,
    )
    mark_absent_claims(record)
    assert record.is_adjudicated()
    assert record.is_complete_fact() is False
    assert record.is_extraction_complete() is False
    assert "procedure_actor" in record.blocking_fields()


# ---------------------------------------------------------------- reviewed is not the same as decided


def test_a_mechanically_decided_claim_is_not_counted_as_reviewed():
    record = _procedure(meaning_supported=Verdict.SUPPORTED)
    mark_absent_claims(record)
    assert "meaning_supported" in record.reviewer_decided_fields()
    assert "procedure_actor" not in record.reviewer_decided_fields()
    summary = score([record])
    assert summary["claims_decided_by"]["absence_from_the_candidate"] > 0
    assert summary["claims_decided_by"]["reviewer"] > 0
    assert summary["human_adjudicated_candidates"] == 0


def test_extraction_completeness_excludes_the_downstream_gates():
    """A parser is not answerable for who issued the document or for learner safety.

    Reporting one completeness number makes a correct extraction look like a failure of the
    parser, when what failed was a gate the parser was never asked to satisfy.
    """
    record = AdjudicationRecord(
        adjudication_id="adj_c", document_key="DOC", document_sha256=None, family="code_meaning",
        candidate_id="10-4", locator="p.1", excerpt="10-4 Message received",
        parser_value={"code": "10-4", "meaning": "Message received"},
        meaning_supported=Verdict.SUPPORTED, code_exact=Verdict.SUPPORTED,
        agency_correct=Verdict.SUPPORTED, region_correct=Verdict.SUPPORTED,
        currentness=Currentness.UNKNOWN,
        issuing_authority_correct=Verdict.MISSING, learner_safe_in_principle=Verdict.WRONG,
    )
    assert record.is_extraction_complete() is True
    assert record.is_complete_fact() is False
    assert set(record.blocking_fields()) == {"issuing_authority_correct", "learner_safe_in_principle"}


# ---------------------------------------------------------------- the committed worksheet


def test_the_committed_worksheet_reproduces_the_audit_totals():
    """Seeding restates the previous review; it must not quietly change what it found."""
    records = read_records(WORKSHEET)
    assert len(records) == 116
    supported = sum(1 for r in records if r.meaning_supported == Verdict.SUPPORTED)
    summary = json.loads((AUDIT / "fact_audit_summary.json").read_text())
    assert supported == summary["meaning_supported"]
    assert all(r.learner_safe_in_principle != Verdict.SUPPORTED for r in records)


def test_the_committed_worksheet_records_that_no_human_reviewed_it():
    records = read_records(WORKSHEET)
    assert not any(r.reviewer_is_human for r in records)
    assert score(records)["any_human_reviewer"] is False


def test_every_remaining_claim_needs_a_document():
    """Nothing decidable without the sources is left open.

    Whatever is still unadjudicated must be a claim a candidate actually made, which cannot be
    judged without reading the document it came from.
    """
    records = read_records(WORKSHEET)
    for r in records:
        for name in r.unadjudicated_fields():
            assert claim_is_carried(r, name) or name == "currentness", (
                f"{r.adjudication_id}: {name} is open but the candidate makes no such claim"
            )


def test_seeding_is_a_restatement_not_a_judgement():
    """Every seeded verdict must trace to a flag the reviewer actually set."""
    audit_rows = [json.loads(line) for line in audit_lines(AUDIT / "fact_audit.jsonl")]
    facts = {json.loads(line)["fact_id"]: json.loads(line) for line in audit_lines(AUDIT / "real_facts.jsonl")}
    records = seed_from_audit(audit_rows, facts, document_keys=DOCUMENT_KEYS)
    by_id = {a["audit_index"]: a for a in audit_rows}
    for i, record in enumerate(records):
        flags = by_id[i]
        assert record.meaning_supported == (Verdict.SUPPORTED if flags["exact_meaning_supported"] else Verdict.WRONG)
        assert record.agency_correct == (Verdict.SUPPORTED if flags["agency_attribution_correct"] else Verdict.WRONG)
        assert record.reviewer == flags["reviewer"]
        assert record.reviewer_is_human == bool(flags["human_review"])


def test_worksheet_round_trips(tmp_path):
    records = read_records(WORKSHEET)
    path = tmp_path / "w.jsonl"
    write_records(records, path)
    assert read_records(path) == records
