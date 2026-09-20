from datetime import date

from radiocorpus.discovery.classify import classify_hit, judge_host, title_mentions_agency
from radiocorpus.discovery.providers import RecordedSearchProvider
from radiocorpus.discovery.stage import discover_from_recorded
from radiocorpus.models import Agency, Source
from radiocorpus.models.common import LeadClass, ResearchStatus, SourceQuality, SourceType, TemporalStatus
from radiocorpus.normalization.temporal import find_effective_date, parse_date
from radiocorpus.provenance.classify import classify_source
from radiocorpus.registry.ingest import ingest_registry
from radiocorpus.registry.resolve import Resolver
from radiocorpus.store import Store
from tests.conftest import CANARY


def test_host_judgement():
    assert judge_host("https://www.chp.ca.gov/x", "California Highway Patrol", "CA").is_official is True
    assert judge_host("https://en.wikipedia.org/wiki/X", "California Highway Patrol", "CA").is_official is False
    assert judge_host("https://wiki.radioreference.com/x", "X", "CA").is_official is False
    assert judge_host("https://lapdonline.org/", "Los Angeles Police Department", "CA").is_official is None  # plausible, unproven
    assert judge_host("https://public.powerdms.com/X", "Maine State Police", "ME").is_official is False


def test_lead_classes():
    lc, _, _ = classify_hit(
        "https://www.flhsmv.gov/pdf/fhp/policies/1401.pdf",
        "POLICY 14.01 Florida Highway Patrol Policy Manual SUBJECT COMMUNICATIONS",
        "",
        "Florida Highway Patrol",
        "FL",
    )
    assert lc == LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE
    lc, _, _ = classify_hit("https://quizlet.com/x", "Kansas Highway Patrol 10-Codes", "", "Kansas Highway Patrol", "KS")
    assert lc == LeadClass.ENTHUSIAST_LEAD
    lc, _, _ = classify_hit(
        "https://www.alea.gov/node/97",
        "State of Alabama Official Website | Alabama Law Enforcement Agency",
        "",
        "Alabama Law Enforcement Agency",
        "AL",
    )
    assert lc == LeadClass.OFFICIAL_HOMEPAGE_CANDIDATE
    lc, _, _ = classify_hit("https://example.com/news", "Local news", "", "X Police Department", "TX")
    assert lc == LeadClass.UNRELATED
    assert title_mentions_agency("Alabama Law Enforcement Agency | Home", "Alabama Law Enforcement Agency")
    assert not title_mentions_agency("ISP: Home", "Indiana State Police")


def test_recorded_provider_separates_not_performed():
    prov = RecordedSearchProvider(CANARY / "discovery_leads.jsonl")
    assert prov.not_performed()  # budget-blocked searches exist in the canary record
    assert all(n.reason for n in prov.not_performed())
    hits = prov.hits_for_subject("CAN-S01")
    assert hits and all(h.url.startswith("http") for h in hits)


def test_discovery_marks_blocked_not_no_public_source(tmp_path):
    s = Store()
    ingest_registry(s, "curated", CANARY / "canary_seed.jsonl")
    Resolver(s).seed_curated("CURATED_CANARY")
    run = discover_from_recorded(s, CANARY / "discovery_leads.jsonl")
    statuses = {a.research_status for a in s.agencies()}
    assert ResearchStatus.NO_PUBLIC_SOURCE not in statuses
    assert ResearchStatus.BLOCKED in statuses and run.stats["blocked_no_search"] > 0
    for a in s.agencies():
        if a.official_website:
            assert "website basis:" in (a.notes or "")
            assert a.research_status in {ResearchStatus.DOMAIN_DISCOVERED, ResearchStatus.DOCUMENTS_DISCOVERED}
    run2 = discover_from_recorded(s, CANARY / "discovery_leads.jsonl")
    assert run2.stats.get("skipped_resumed") == 100


def test_date_parsing_and_undated_stays_none():
    assert parse_date("Effective: March 1, 2024") == date(2024, 3, 1)
    assert parse_date("Revised 3/3/2006") == date(2006, 3, 3)
    assert parse_date("2021-06-01 v2") == date(2021, 6, 1)
    assert find_effective_date("General order 12. Revised: January 15, 2023.") == date(2023, 1, 15)
    assert find_effective_date("POLICY 300 COMMUNICATIONS 300.4 RADIO CODES") is None
    assert find_effective_date("Effective on receipt. Page 4 of 10-4.") is None


def _src(**kw):
    base = dict(
        source_id="s",
        source_type=SourceType.AGENCY_POLICY_MANUAL,
        title="t",
        issuing_authority=None,
        agency_or_jurisdiction="agy",
        canonical_url="https://police.city.gov/manual.pdf",
        document_hash="sha256:aa",
    )
    base.update(kw)
    return Source(**base)


def test_source_classification_rules():
    # Legacy date/TLD-only assertions were unsafe. Identity is now separately required.
    today = date(2026, 9, 20)
    for source in [_src(), _src(effective_date=date(2024, 1, 1)), _src(effective_date=date(2009, 1, 1))]:
        assert classify_source(source, "City Police Department", "TX", today)[:2] == (SourceQuality.UNVERIFIED, TemporalStatus.UNCERTAIN)


def test_agency_model_unknown_defaults():
    a = Agency(agency_id="x", canonical_name="X")
    assert a.official_website is None and a.dispatch_provider is None and a.state is None
    assert a.status == "unknown" and a.research_status == "unknown" and a.agency_type == "unknown"
