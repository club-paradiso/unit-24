"""Regression: search-name overlap must not establish entity identity."""
import pytest

from radiocorpus.discovery.classify import title_mentions_agency


@pytest.mark.parametrize('target,candidate', [
    ('Miami Police Department', 'South Miami Police Department'),
    ('Miami Police Department', 'Miami Beach Police Department'),
    ('Miami Police Department', 'Miami-Dade Police Department'),
    ('Miami Police Department', "Miami-Dade Sheriff's Office"),
    ('South Miami Police Department', 'Miami Police Department'),
    ('Berkeley Police Department', 'University of California Berkeley Police Department'),
    ('Portland Police Department Maine', 'Portland Police Department Oregon'),
    ('Washington State Patrol', 'Washington DC Metropolitan Police Department'),
    ('Orange County Sheriff California', 'Orange County Sheriff Florida'),
])
def test_distinct_entities_are_not_title_matches(target, candidate):
    assert not title_mentions_agency(candidate, target)
