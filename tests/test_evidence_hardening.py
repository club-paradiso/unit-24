"""Adversarial policy tests; synthetic assertions are never real agency evidence."""

from datetime import date, timedelta

import pytest

from radiocorpus.conflicts.detect import _try_resolve
from radiocorpus.eligibility.policy import decide_fact
from radiocorpus.models import Agency, Source
from radiocorpus.models.common import Currentness, EligibilityState, ReviewStatus, SourceQuality
from radiocorpus.models.evidence import CurrentnessEvidence, IdentityEvidence, ProtocolApplicabilityEvidence
from radiocorpus.provenance.classify import classify_source
from radiocorpus.provenance.evidence import applicability_matches, currentness, independently_corroborated
from tests.test_eligibility_invariants import _fact, _src


def official(sid="src_1", year=2024):
    src = _src()
    return Source.model_validate(
        {
            **src.model_dump(),
            "source_id": sid,
            "effective_date": date(year, 1, 1),
            "host_matches_target_entity": True,
            "identity_evidence": IdentityEvidence(
                evidence_source_id=sid,
                locator="p.1",
                excerpt="A Police Department, Texas",
                verified_by="synthetic reviewer",
                verification_status="verified",
                target_agency_id="agy_a",
                canonical_name="A Police Department",
                state="TX",
                host="a.gov",
                basis="agency_page",
            ),
            "document_hash": "sha256:" + sid,
            "canonical_url": "https://a.gov/" + sid + ".pdf",
        }
    )


def confirmed(src):
    return src.model_copy(
        update={
            "currentness_evidence": CurrentnessEvidence(
                evidence_source_id=src.source_id,
                target_source_id=src.source_id,
                locator="policy index item",
                excerpt="Active policy",
                verification_status="verified",
                verified_by="synthetic reviewer",
                basis="active_policy_portal",
                checked_on=date.today(),
                recheck_by=date.today() + timedelta(days=30),
            )
        }
    )


def accepted_fact(source=None, **kwargs):
    from radiocorpus.models.evidence import FactReviewEvidence

    source = source or confirmed(official())
    fact = _fact(review_status=ReviewStatus.HUMAN_ACCEPTED, temporal_status="current", **kwargs)
    fact.review_evidence = FactReviewEvidence(
        fact_id=fact.fact_id,
        source_id=fact.source_id,
        document_hash=source.document_hash,
        value_fingerprint=fact.value_fingerprint(),
        reviewer_id="synthetic human",
        reviewer_kind="human",
        reviewed_on=date.today(),
        decision="accepted",
    )
    return fact


@pytest.mark.parametrize("year", [1990, 2018, 2025, 2026])
def test_age_does_not_establish_current(year):
    src = official(year=year)
    assert currentness(src, date(2026, 9, 20)) == Currentness.UNKNOWN
    assert classify_source(src, "A Police Department", "TX", date(2026, 9, 20))[0] == SourceQuality.OFFICIAL_PARTIAL


def test_undated_current_portal_requires_explicit_evidence():
    src = official().model_copy(update={"effective_date": None})
    assert currentness(src) == Currentness.UNDATED
    assert currentness(confirmed(src)) == Currentness.CONFIRMED


def test_recent_superseded_wins_over_current_marker():
    src = confirmed(official()).model_copy(update={"superseded_by": "new"})
    assert currentness(src) == Currentness.SUPERSEDED


def test_future_effective_policy_not_current():
    src = confirmed(official())
    src.currentness_evidence.effective_from = date(2099, 1, 1)
    assert currentness(src) == Currentness.UNKNOWN


def test_parser_never_auto_verified_even_from_confirmed_source():
    assert decide_fact(_fact(), confirmed(official()), [], None, False)[1].state == EligibilityState.RESEARCH_ONLY
    assert decide_fact(accepted_fact(), confirmed(official()), [], None, False)[1].state == EligibilityState.PLAYABLE_VERIFIED


@pytest.mark.parametrize("mode", ["same_hash", "copied_html", "enthusiasts", "unknown_lineage"])
def test_repetition_not_independence(mode):
    a, b = official("a"), official("b")
    a.issuing_authority_id = "issuer_a"
    b.issuing_authority_id = "issuer_b"
    a.evidence_lineage = ["origin_a"]
    b.evidence_lineage = ["origin_b"]
    if mode == "same_hash":
        b.document_hash = a.document_hash
    elif mode == "copied_html":
        b.evidence_lineage = a.evidence_lineage
    elif mode == "enthusiasts":
        a.source_quality = SourceQuality.UNVERIFIED
        b.source_quality = SourceQuality.UNVERIFIED
    else:
        b.evidence_lineage = []
    assert not independently_corroborated([a, b])


def test_independent_government_sources():
    a, b = official("a"), official("b")
    a.issuing_authority_id = "issuer_a"
    b.issuing_authority_id = "issuer_b"
    a.evidence_lineage = ["origin_a"]
    b.evidence_lineage = ["origin_b"]
    assert independently_corroborated([a, b])


@pytest.mark.parametrize("relationship", ["parent_agency", "dispatch_provider"])
def test_relationship_is_not_applicability(store, relationship):
    store.upsert_agency(Agency(agency_id="agy_a", canonical_name="A", **{relationship: "agy_b"}))
    source = official().model_copy(update={"agency_or_jurisdiction": "agy_b"})
    assert not applicability_matches(store, _fact(), source)


def test_named_dispatch_members_and_scope_only(store, tmp_path):
    src = official().model_copy(update={"agency_or_jurisdiction": "agy_dispatch"})
    from radiocorpus.ids import document_hash
    from radiocorpus.models import DocumentRecord

    path = tmp_path / "membership.txt"
    path.write_text("Agency A uses regional 10-4. Unit identifiers remain agency-specific.")
    src.document_hash = document_hash(path.read_bytes())
    store.insert_document(
        DocumentRecord(
            source_id=src.source_id, document_hash=src.document_hash, local_path=str(path), content_type="text/plain", byte_length=path.stat().st_size
        )
    )
    store.insert_source(src)
    src.applicability = [
        ProtocolApplicabilityEvidence(
            evidence_source_id=src.source_id,
            locator="p.2 membership and codes",
            excerpt="Agency A uses regional 10-4. Unit identifiers remain agency-specific.",
            verification_status="verified",
            verified_by="synthetic reviewer",
            source_agency_or_dispatcher="agy_dispatch",
            target_agency="agy_a",
            protocol_source_id=src.source_id,
            scope=["code_meaning"],
            fact_keys=["10-4"],
            effective_from=date(2020, 1, 1),
        )
    ]
    assert applicability_matches(store, _fact(), src)
    assert not applicability_matches(store, _fact(agency_id="agy_b"), src)  # incomplete member list
    assert not applicability_matches(store, _fact(key="unit"), src)  # shared dispatch, different units


def test_newer_dated_policy_cannot_resolve_conflict():
    a, b = official("a", 2020), official("b", 2026)
    f1, f2 = _fact(source_id="a"), _fact(fact_id="f2", source_id="b")
    f2.value.meaning = "Different"
    sources = {"a": a, "b": b}
    assert _try_resolve([f1, f2], sources.get)[0] == "unresolved"
    a.superseded_by = "b"
    assert _try_resolve([f1, f2], sources.get)[0] == "unresolved"  # an unbound link alone is not proof


def test_currentness_observation_expires():
    source = confirmed(official())
    source.currentness_evidence.checked_on = date(2000, 1, 1)
    source.currentness_evidence.recheck_by = date(2000, 2, 1)
    assert currentness(source) == Currentness.PRESUMED


def test_review_enum_without_human_attribution_cannot_play():
    source = confirmed(official())
    assert decide_fact(_fact(review_status=ReviewStatus.HUMAN_ACCEPTED), source, [], None, False)[1].state == EligibilityState.RESEARCH_ONLY
    fact = accepted_fact(source)
    fact.review_evidence.reviewer_kind = "model"
    assert decide_fact(fact, source, [], None, False)[1].state == EligibilityState.RESEARCH_ONLY


def test_uncertain_fact_cannot_play_even_after_human_acceptance():
    source = confirmed(official())
    fact = accepted_fact(source)
    fact.temporal_status = "uncertain"
    assert decide_fact(fact, source, [], None, False)[1].state == EligibilityState.RESEARCH_ONLY
