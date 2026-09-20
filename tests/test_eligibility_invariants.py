from datetime import date

from radiocorpus import ids
from radiocorpus.eligibility.policy import decide_fact
from radiocorpus.invariants import inv_no_cross_agency_synthesis, inv_playable_requires_official_evidence, inv_unknown_stays_unknown
from radiocorpus.models import Agency, CodeMeaning, EligibilityDecision, ProtocolFact, Source
from radiocorpus.models.common import (
    EligibilityState,
    ExtractionMethod,
    FactType,
    ReviewStatus,
    SourceQuality,
    SourceType,
    VerificationStatus,
)


def _src(q=SourceQuality.OFFICIAL_CURRENT, t=SourceType.AGENCY_POLICY_MANUAL, agency="agy_a", h="sha256:ab"):
    return Source(
        source_id="src_1",
        source_type=t,
        title="T",
        issuing_authority=None,
        agency_or_jurisdiction=agency,
        canonical_url="https://a.gov/x.pdf",
        document_hash=h,
        source_quality=q,
        effective_date=date(2024, 1, 1),
    )


def _fact(**kw):
    base = dict(
        fact_id="fct_1",
        agency_id="agy_a",
        fact_type=FactType.CODE_MEANING,
        key="10-4",
        value=CodeMeaning(code_system="TEN_CODE", code="10-4", meaning="Ack"),
        source_id="src_1",
        locator="p.1",
        excerpt="10-4 Ack",
        confidence=0.9,
        extraction_method=ExtractionMethod.DETERMINISTIC_PARSER,
    )
    base.update(kw)
    return ProtocolFact(**base)


def test_policy_matrix():
    assert decide_fact(_fact(), _src(), [], None, False)[1].state == EligibilityState.PLAYABLE_VERIFIED
    assert decide_fact(_fact(), _src(SourceQuality.OFFICIAL_PARTIAL), [], None, False)[1].state == EligibilityState.PLAYABLE_WITH_LIMITATIONS
    assert decide_fact(_fact(), _src(SourceQuality.OFFICIAL_HISTORICAL), [], None, False)[1].state == EligibilityState.HISTORICAL_ONLY
    assert decide_fact(_fact(), _src(), ["cfl_1"], None, False)[1].state == EligibilityState.CONFLICT_REQUIRES_REVIEW
    assert (
        decide_fact(_fact(), _src(SourceQuality.UNVERIFIED, SourceType.ENTHUSIAST_OR_CROWDSOURCED), [], None, False)[1].state
        == EligibilityState.RESEARCH_ONLY
    )
    vs, dec = decide_fact(_fact(), _src(SourceQuality.UNVERIFIED, SourceType.SECONDARY_PUBLICATION), [], None, True)
    assert dec.state == EligibilityState.PLAYABLE_WITH_LIMITATIONS and vs == VerificationStatus.CORROBORATED
    model = _fact(extraction_method=ExtractionMethod.MODEL, extraction_model="m", review_status=ReviewStatus.NEEDS_REVIEW)
    assert decide_fact(model, _src(), [], None, False)[1].state == EligibilityState.RESEARCH_ONLY
    accepted = model.model_copy(update={"review_status": ReviewStatus.HUMAN_ACCEPTED})
    assert decide_fact(accepted, _src(), [], None, False)[1].state == EligibilityState.PLAYABLE_VERIFIED
    assert (
        decide_fact(_fact(verification_status=VerificationStatus.REJECTED), _src(), [], None, False)[1].state
        == EligibilityState.INSUFFICIENT_EVIDENCE
    )
    assert decide_fact(_fact(), _src(), [], ("cfl_2", "resolved_temporal"), False)[1].state == EligibilityState.HISTORICAL_ONLY
    assert decide_fact(_fact(), _src(), [], ("cfl_2", "resolved_jurisdictional"), False)[1].state == EligibilityState.RESEARCH_ONLY


def test_invariant_catches_playable_without_official_source(store):
    store.upsert_agency(Agency(agency_id="agy_a", canonical_name="A", state="TX"))
    store.insert_source(_src(SourceQuality.UNVERIFIED, SourceType.SECONDARY_PUBLICATION))
    store.insert_fact(_fact())
    store.upsert_eligibility(
        EligibilityDecision(subject_kind="fact", subject_id="fct_1", state=EligibilityState.PLAYABLE_VERIFIED, reasons=["forged"], policy_version="t")
    )
    assert inv_playable_requires_official_evidence(store)


def test_invariant_catches_cross_agency_synthesis(store):
    store.upsert_agency(Agency(agency_id="agy_a", canonical_name="A", state="TX"))
    store.upsert_agency(Agency(agency_id="agy_b", canonical_name="B", state="TX"))
    store.insert_source(_src(agency="agy_b"))
    store.insert_fact(_fact(agency_id="agy_a"))  # cites the neighbour's document
    assert inv_no_cross_agency_synthesis(store)


def test_invariant_unknown_stays_unknown(store):
    store.upsert_agency(
        Agency(agency_id="agy_a", canonical_name="A", state="TX", official_website="https://a.gov/", research_status="domain_discovered")
    )
    assert inv_unknown_stays_unknown(store)  # website without recorded basis
    store.upsert_agency(
        Agency(
            agency_id="agy_a",
            canonical_name="A",
            state="TX",
            official_website="https://a.gov/",
            research_status="domain_discovered",
            notes="website basis: search A rank 1",
        )
    )
    assert not inv_unknown_stays_unknown(store)


def test_source_status_changes_are_audited(store):
    store.insert_source(_src(SourceQuality.UNVERIFIED))
    store.update_source_status("src_1", field="source_quality", new_value=SourceQuality.OFFICIAL_CURRENT, reason="test")
    assert store.get_source("src_1").source_quality == SourceQuality.OFFICIAL_CURRENT
    assert store.raw("select count(*) c from source_events")[0]["c"] == 1
    try:
        store.update_source_status("src_1", field="canonical_url", new_value="https://x", reason="nope")
        raise AssertionError
    except ValueError:
        pass


def test_document_hash_helper():
    assert ids.document_hash(b"abc") == "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert ids.fact_id("a", "t", "k", "s", "l", "v") == ids.fact_id("a", "t", "k", "s", "l", "v")
    assert ids.fact_id("a", "t", "k", "s", "l", "v") != ids.fact_id("a", "t", "k", "s", "l", "w")
