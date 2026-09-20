"""End-to-end behaviour on the synthetic fixture corpus."""

from pathlib import Path

from radiocorpus.conflicts.detect import detect_conflicts
from radiocorpus.eligibility.policy import assign_all, explain
from radiocorpus.extraction.stage import extract_all
from radiocorpus.invariants import check_all
from radiocorpus.models.common import ConflictResolution, EligibilityState, SourceQuality, TemporalStatus, VerificationStatus
from radiocorpus.stats import corpus_stats
from tests.conftest import fixture_agency_id, run_fixture_pipeline


def _elig(store, fid):
    return next(e for e in store.eligibility("fact") if e.subject_id == fid)


def _facts(store, fx, key):
    return store.facts(fixture_agency_id(fx)) and [f for f in store.facts(fixture_agency_id(fx)) if f.key == key]


def test_all_invariants_hold(fixture_store):
    assert {k: v for k, v in check_all(fixture_store).items() if v} == {}


def test_current_vs_historical_resolved_temporally_and_preserved(fixture_store):
    s = fixture_store
    facts = _facts(s, "FX-001", "10-50")
    by_src = {s.get_source(f.source_id).title: f for f in facts}
    new, old, fan = (
        by_src["Policy 4.10 Radio Communications"],
        by_src["General Order 2009-05 Radio Procedures"],
        by_src["Exampleville PD scanner codes (fan page)"],
    )
    assert len(facts) == 3  # nothing deleted
    assert _elig(s, new.fact_id).state == EligibilityState.PLAYABLE_VERIFIED
    assert old.temporal_status == TemporalStatus.HISTORICAL and old.superseded_by == new.fact_id
    assert _elig(s, old.fact_id).state == EligibilityState.HISTORICAL_ONLY
    assert fan.verification_status == VerificationStatus.UNVERIFIED and fan.temporal_status != TemporalStatus.HISTORICAL
    assert _elig(s, fan.fact_id).state == EligibilityState.RESEARCH_ONLY
    c = next(c for c in s.conflicts() if c.key == "10-50")
    assert c.resolution == ConflictResolution.RESOLVED_TEMPORAL and c.preferred_fact_id == new.fact_id
    assert any(e["field"] == "temporal_status" for e in s.fact_events(old.fact_id))  # audited transition


def test_agreeing_values_across_current_and_old_manual_are_not_conflicts(fixture_store):
    s = fixture_store
    facts = _facts(s, "FX-001", "10-33")
    assert len(facts) == 3 and not [c for c in s.conflicts() if c.key == "10-33"]
    states = {_elig(s, f.fact_id).state for f in facts}
    assert EligibilityState.PLAYABLE_VERIFIED in states


def test_agency_vs_dispatch_resolved_jurisdictionally(fixture_store):
    s = fixture_store
    c = next(c for c in s.conflicts() if c.key == "10-7" and c.agency_id == fixture_agency_id("FX-002"))
    assert c.kind == "agency_vs_dispatch" and c.resolution == ConflictResolution.RESOLVED_JURISDICTIONAL
    pref = s.get_fact(c.preferred_fact_id)
    assert s.get_source(pref.source_id).source_type == "agency_policy_manual"
    assert _elig(s, pref.fact_id).state == EligibilityState.PLAYABLE_WITH_LIMITATIONS  # undated manual => limited
    loser = next(f for f in _facts(s, "FX-002", "10-7") if f.fact_id != pref.fact_id)
    assert _elig(s, loser.fact_id).state == EligibilityState.RESEARCH_ONLY and loser.temporal_status != TemporalStatus.HISTORICAL


def test_same_date_official_disagreement_stays_unresolved(fixture_store):
    s = fixture_store
    c = next(c for c in s.conflicts() if c.key == "SIGNAL 7")
    assert c.resolution == ConflictResolution.UNRESOLVED and c.preferred_fact_id is None
    for fid in c.fact_ids:
        assert _elig(s, fid).state == EligibilityState.CONFLICT_REQUIRES_REVIEW
        assert s.get_fact(fid).verification_status == VerificationStatus.UNVERIFIED


def test_undated_official_manual_is_partial_not_current(fixture_store):
    src = next(x for x in fixture_store.sources() if x.title == "Policy 300 Communications")
    assert src.source_quality == SourceQuality.OFFICIAL_PARTIAL and src.temporal_status == TemporalStatus.UNCERTAIN


def test_secondary_source_never_verified(fixture_store):
    fan = next(x for x in fixture_store.sources() if "scanner" in (x.title or ""))
    assert fan.source_quality == SourceQuality.UNVERIFIED
    for f in fixture_store.facts():
        if f.source_id == fan.source_id:
            assert f.verification_status != VerificationStatus.VERIFIED
            assert _elig(fixture_store, f.fact_id).state in {EligibilityState.RESEARCH_ONLY, EligibilityState.PLAYABLE_WITH_LIMITATIONS}


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
    assert st["total_agencies"] == 5 and st["conflict_count"] == 3 and st["unresolved_conflict_count"] == 1
    assert st["verified_fact_count"] > 0 and st["training_eligible_agency_count"] == 3


def test_conflict_detection_rerun_keeps_ids_stable(fixture_store):
    ids_before = {c.conflict_id for c in fixture_store.conflicts()}
    detect_conflicts(fixture_store)
    assign_all(fixture_store)
    assert {c.conflict_id for c in fixture_store.conflicts()} == ids_before
