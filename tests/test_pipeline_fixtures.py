"""End-to-end behaviour on the synthetic fixture corpus."""

from pathlib import Path

from radiocorpus.conflicts.detect import detect_conflicts
from radiocorpus.eligibility.policy import assign_all, explain
from radiocorpus.extraction.stage import extract_all
from radiocorpus.invariants import check_all
from radiocorpus.models.common import ConflictResolution, EligibilityState, SourceQuality, VerificationStatus
from radiocorpus.stats import corpus_stats
from tests.conftest import fixture_agency_id, run_fixture_pipeline


def _elig(store, fid):
    return next(e for e in store.eligibility("fact") if e.subject_id == fid)


def _facts(store, fx, key):
    return store.facts(fixture_agency_id(fx)) and [f for f in store.facts(fixture_agency_id(fx)) if f.key == key]


def test_all_invariants_hold(fixture_store):
    assert {k: v for k, v in check_all(fixture_store).items() if v} == {}


def test_legacy_fixtures_are_preserved_but_not_promoted(fixture_store):
    # Old fixtures asserted currency from age and authority from type. No new evidence is fabricated.
    assert len(fixture_store.facts()) >= 89  # leaf HTML paragraphs now contribute additional candidates
    assert all(
        e.state not in {EligibilityState.PLAYABLE_VERIFIED, EligibilityState.PLAYABLE_WITH_LIMITATIONS} for e in fixture_store.eligibility("fact")
    )
    assert all(c.resolution == ConflictResolution.UNRESOLVED for c in fixture_store.conflicts())


def test_agreeing_values_are_not_conflicts(fixture_store):
    assert not [c for c in fixture_store.conflicts() if c.key == "10-33"]


def test_undated_fixture_no_longer_bypasses_identity(fixture_store):
    src = next(x for x in fixture_store.sources() if x.title == "Policy 300 Communications")
    assert src.source_quality == SourceQuality.UNVERIFIED


def test_secondary_source_never_verified(fixture_store):
    fan = next(x for x in fixture_store.sources() if "scanner" in (x.title or ""))
    assert fan.source_quality == SourceQuality.UNVERIFIED
    for f in fixture_store.facts():
        if f.source_id == fan.source_id:
            assert f.verification_status != VerificationStatus.VERIFIED
            assert _elig(fixture_store, f.fact_id).state in {EligibilityState.RESEARCH_ONLY, EligibilityState.CONFLICT_REQUIRES_REVIEW}


def test_unknown_agency_stays_unknown_despite_shared_dispatch(fixture_store):
    """FX-004 shares a dispatch centre with FX-001 and FX-002 but has no documents: nothing may be synthesised."""
    s = fixture_store
    nb = fixture_agency_id("FX-004")
    assert s.facts(nb) == []
    e = next(e for e in s.eligibility("agency") if e.subject_id == nb)
    assert e.state == EligibilityState.INSUFFICIENT_EVIDENCE
    assert s.get_agency(nb).official_website is None


def test_explain_returns_evidence_only(fixture_store):
    f = _facts(fixture_store, "FX-001", "10-4")[0]
    ex = explain(fixture_store, f.fact_id)
    assert ex["source"]["document_hash"].startswith("sha256:") and ex["locator"] and ex["excerpt"]
    assert ex["eligibility_reasons"]


def test_repeat_run_is_idempotent(tmp_path, fixture_store):
    s = fixture_store
    before = (len(s.facts()), len(s.conflicts()), len(s.sources()))
    run_fixture_pipeline(s, tmp_path / "docs2")
    assert (len(s.facts()), len(s.conflicts()), len(s.sources())) == before
    run = extract_all(s)
    assert run.stats.get("skipped_resumed") == 7 and run.stats.get("facts_inserted", 0) == 0


def test_document_hashing_is_content_addressed(tmp_path, fixture_store):
    docs = fixture_store.documents()
    assert len(docs) == 7 and all(d.document_hash.startswith("sha256:") for d in docs)
    for d in docs:
        assert Path(d.local_path).name.split(".")[0] == d.document_hash.split(":")[1]


def test_newer_extraction_never_overwrites_existing_fact(fixture_store):
    s = fixture_store
    f = s.facts()[0]
    mutated = f.model_copy(update={"excerpt": "MUTATED"})
    assert s.insert_fact(mutated) is False
    assert s.get_fact(f.fact_id).excerpt != "MUTATED"


def test_stats_exclude_fixtures_by_default(fixture_store):
    assert corpus_stats(fixture_store)["total_agencies"] == 0
    st = corpus_stats(fixture_store, include_fixtures=True)
    # Parser v3 emits fewer spurious candidates, so fewer spurious conflicts arise. The
    # conflicts that carry the safety properties must all still be present and unresolved.
    assert st["total_agencies"] == 5
    assert st["conflict_count"] == 5 and st["unresolved_conflict_count"] == 5
    keys = {c.key for c in fixture_store.conflicts()}
    assert {"10-7", "SIGNAL 7", "10-50"} <= keys, "agency-vs-dispatch, same-date and current-vs-obsolete conflicts must survive"
    assert st["verified_fact_count"] == 0 and st["training_eligible_agency_count"] == 0


def test_conflict_detection_rerun_keeps_ids_stable(fixture_store):
    ids_before = {c.conflict_id for c in fixture_store.conflicts()}
    detect_conflicts(fixture_store)
    assign_all(fixture_store)
    assert {c.conflict_id for c in fixture_store.conflicts()} == ids_before
