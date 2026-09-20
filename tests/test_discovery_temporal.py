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
    assert prov.not_performed()  # one skipped search (no official host identified) remains in the record
    assert all(n.reason for n in prov.not_performed())
    hits = prov.hits_for_subject("CAN-S01")
    assert hits and all(h.url.startswith("http") for h in hits)


def test_discovery_marks_blocked_not_no_public_source(tmp_path):
    """A not-performed search yields BLOCKED, never NO_PUBLIC_SOURCE; a judgment-only agency is also BLOCKED."""
    import json

    s = Store()
    ingest_registry(s, "curated", CANARY / "canary_seed.jsonl")
    Resolver(s).seed_curated("CURATED_CANARY")
    leads = tmp_path / "leads.jsonl"
    rows = [
        {"record_type": "search_not_performed", "canary_id": "CAN-S01", "seed_name": "Alabama Law Enforcement Agency",
         "query": "q", "search_index": "A", "reason": "budget", "retrieved_at": "2026-09-20T05:00:00Z"},
        {"record_type": "worker_judgment", "canary_id": "CAN-S02", "official_domain_candidate": None, "basis": "",
         "agency_existence_signal": "none", "notes": "NOT PROCESSED"},
        {"record_type": "search_result", "canary_id": "CAN-S05", "seed_name": "California Highway Patrol",
         "query": '"California Highway Patrol" CA official website', "search_index": "A", "rank": 1,
         "title": "California Highway Patrol | Home", "url": "https://www.chp.ca.gov/", "snippet": "", "retrieved_at": "2026-09-20T05:00:00Z"},
    ]
    leads.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    run = discover_from_recorded(s, leads)
    by = {a.source_registry_ids["CURATED_CANARY"][0]: a for a in s.agencies()}
    assert by["CAN-S01"].research_status == ResearchStatus.BLOCKED and "not performed" in (by["CAN-S01"].notes or "")
    assert by["CAN-S02"].research_status == ResearchStatus.BLOCKED
    assert by["CAN-S05"].research_status == ResearchStatus.DOMAIN_DISCOVERED and by["CAN-S05"].official_website == "https://www.chp.ca.gov/"
    assert "website basis:" in (by["CAN-S05"].notes or "")
    assert by["CAN-S03"].research_status == ResearchStatus.SEED_UNCONFIRMED  # no record at all: nothing claimed
    assert ResearchStatus.NO_PUBLIC_SOURCE not in {a.research_status for a in s.agencies()}
    assert run.stats["blocked_no_search"] == 2
    run2 = discover_from_recorded(s, leads)
    assert run2.stats.get("skipped_resumed") == 100


def test_full_canary_discovery_record(tmp_path):
    """The committed canary record: every agency searched, websites only with a basis."""
    s = Store()
    ingest_registry(s, "curated", CANARY / "canary_seed.jsonl")
    Resolver(s).seed_curated("CURATED_CANARY")
    run = discover_from_recorded(s, CANARY / "discovery_leads.jsonl")
    assert run.stats.get("blocked_no_search", 0) == 0 and run.stats["agencies"] == 100
    for a in s.agencies():
        if a.official_website:
            assert "website basis:" in (a.notes or "")
            assert a.research_status in {ResearchStatus.DOMAIN_DISCOVERED, ResearchStatus.DOCUMENTS_DISCOVERED}
        assert a.research_status != ResearchStatus.NO_PUBLIC_SOURCE


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
    today = date(2026, 9, 20)
    q, t, _ = classify_source(_src(effective_date=date(2024, 1, 1)), "City Police Department", "TX", today)
    assert (q, t) == (SourceQuality.OFFICIAL_CURRENT, TemporalStatus.CURRENT)
    q, t, _ = classify_source(_src(), "City Police Department", "TX", today)
    assert (q, t) == (SourceQuality.OFFICIAL_PARTIAL, TemporalStatus.UNCERTAIN)
    q, _, _ = classify_source(_src(effective_date=date(2009, 1, 1)), "City Police Department", "TX", today)
    assert q == SourceQuality.OFFICIAL_PARTIAL
    q, t, _ = classify_source(_src(effective_date=date(2024, 1, 1), superseded_by="s2"), "City Police Department", "TX", today)
    assert (q, t) == (SourceQuality.OFFICIAL_HISTORICAL, TemporalStatus.HISTORICAL)
    q, _, _ = classify_source(
        _src(canonical_url="https://wiki.radioreference.com/x", effective_date=date(2024, 1, 1)), "City Police Department", "TX", today
    )
    assert q == SourceQuality.UNVERIFIED  # official type claimed, but host is not official
    q, _, _ = classify_source(_src(document_hash=None), "City Police Department", "TX", today)
    assert q == SourceQuality.UNVERIFIED


def test_agency_model_unknown_defaults():
    a = Agency(agency_id="x", canonical_name="X")
    assert a.official_website is None and a.dispatch_provider is None and a.state is None
    assert a.status == "unknown" and a.research_status == "unknown" and a.agency_type == "unknown"
