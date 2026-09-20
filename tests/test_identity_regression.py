"""Regression: search-name overlap must not establish entity identity."""

import pytest

from radiocorpus.discovery.classify import title_mentions_agency


@pytest.mark.parametrize(
    "target,candidate",
    [
        ("Miami Police Department", "South Miami Police Department"),
        ("Miami Police Department", "Miami Beach Police Department"),
        ("Miami Police Department", "Miami-Dade Police Department"),
        ("Miami Police Department", "Miami-Dade Sheriff's Office"),
        ("South Miami Police Department", "Miami Police Department"),
        ("Berkeley Police Department", "University of California Berkeley Police Department"),
        ("Portland Police Department Maine", "Portland Police Department Oregon"),
        ("Washington State Patrol", "Washington DC Metropolitan Police Department"),
        ("Orange County Sheriff California", "Orange County Sheriff Florida"),
    ],
)
def test_distinct_entities_are_not_title_matches(target, candidate):
    assert not title_mentions_agency(candidate, target)


@pytest.mark.parametrize(
    "target_name,target_state,candidate_name,candidate_state",
    [
        ("Miami Police Department", "FL", "South Miami Police Department", "FL"),
        ("Miami Police Department", "FL", "Miami Beach Police Department", "FL"),
        ("Berkeley Police Department", "CA", "University of California Berkeley Police Department", "CA"),
        ("Portland Police Department", "ME", "Portland Police Department", "OR"),
        ("Washington State Patrol", "WA", "Metropolitan Police Department", "DC"),
        ("Orange County Sheriff's Office", "CA", "Orange County Sheriff's Office", "FL"),
    ],
)
def test_explicit_identity_cannot_cross_name_or_state(target_name, target_state, candidate_name, candidate_state):
    from radiocorpus.discovery.identity import verified_website
    from radiocorpus.models import Agency
    from radiocorpus.models.evidence import IdentityEvidence

    agency = Agency(agency_id="target", canonical_name=target_name, state=target_state)
    evidence = IdentityEvidence(
        evidence_source_id="source",
        locator="h1",
        excerpt=candidate_name,
        verification_status="verified",
        verified_by="synthetic reviewer",
        target_agency_id="target",
        canonical_name=candidate_name,
        state=candidate_state,
        host="example.gov",
        basis="agency_page",
    )
    assert not verified_website(agency, "https://example.gov", evidence)
