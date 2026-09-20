"""Corpus statistics (observability). Fixture agencies/sources are excluded unless asked."""

from __future__ import annotations

from collections import Counter
from typing import Any

from radiocorpus.models.common import AcquisitionStatus, EligibilityState, FactType, LeadClass, ResearchStatus, SourceQuality, VerificationStatus
from radiocorpus.store import Store


def corpus_stats(store: Store, *, registry_filter: str | None = None, include_fixtures: bool = False) -> dict[str, Any]:
    agencies = [a for a in store.agencies(include_fixtures=include_fixtures) if registry_filter is None or registry_filter in a.source_registry_ids]
    aid = {a.agency_id for a in agencies}
    by_state = Counter(a.state or "UNKNOWN" for a in agencies)
    by_type = Counter(a.agency_type for a in agencies)
    by_research = Counter(a.research_status for a in agencies)
    leads = [lead for lead in store.leads() if lead.agency_id in aid]
    sources = [s for s in store.sources(include_fixtures=include_fixtures) if s.agency_or_jurisdiction in aid]
    facts = [f for f in store.facts() if f.agency_id in aid]
    conflicts = [c for c in store.conflicts() if c.agency_id in aid]
    elig_agency = {e.subject_id: e.state for e in store.eligibility("agency") if e.subject_id in aid}

    def fact_agencies(t: str) -> int:
        return len({f.agency_id for f in facts if f.fact_type == t and f.verification_status != VerificationStatus.REJECTED})

    official_current = [s for s in sources if s.source_quality == SourceQuality.OFFICIAL_CURRENT]
    historical = [s for s in sources if s.source_quality == SourceQuality.OFFICIAL_HISTORICAL]
    return {
        "total_agencies": len(agencies),
        "agencies_by_state": dict(sorted(by_state.items())),
        "agencies_by_type": dict(sorted(by_type.items())),
        "agencies_by_research_status": dict(sorted(by_research.items())),
        "official_domains_discovered": sum(1 for a in agencies if a.official_website),
        "documents_discovered": sum(
            1
            for lead in leads
            if lead.lead_class
            in {LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE, LeadClass.OFFICIAL_DOCUMENT_CANDIDATE, LeadClass.STANDARDS_BODY_DOCUMENT}
        ),
        "radio_policy_candidates_discovered": sum(1 for lead in leads if lead.lead_class == LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE),
        "leads_total": len(leads),
        "leads_by_class": dict(Counter(lead.lead_class for lead in leads)),
        "leads_by_acquisition_status": dict(Counter(lead.acquisition_status for lead in leads)),
        "documents_acquired": len({s.document_hash for s in sources if s.document_hash}),
        "current_official_documents": len(official_current),
        "historical_documents": len(historical),
        "sources_by_quality": dict(Counter(s.source_quality for s in sources)),
        "agencies_with_code_data": fact_agencies(FactType.CODE_MEANING),
        "agencies_with_phonetic_data": fact_agencies(FactType.PHONETIC_LETTER),
        "agencies_with_procedural_data": fact_agencies(FactType.PROCEDURE_RULE),
        "conflict_count": len(conflicts),
        "unresolved_conflict_count": sum(1 for c in conflicts if c.resolution == "unresolved"),
        "verified_fact_count": sum(1 for f in facts if f.verification_status == VerificationStatus.VERIFIED),
        "corroborated_fact_count": sum(1 for f in facts if f.verification_status == VerificationStatus.CORROBORATED),
        "unverified_candidate_count": sum(1 for f in facts if f.verification_status == VerificationStatus.UNVERIFIED),
        "rejected_fact_count": sum(1 for f in facts if f.verification_status == VerificationStatus.REJECTED),
        "no_public_source_count": sum(1 for a in agencies if a.research_status == ResearchStatus.NO_PUBLIC_SOURCE),
        "blocked_agency_count": sum(1 for a in agencies if a.research_status == ResearchStatus.BLOCKED),
        "training_eligible_agency_count": sum(
            1 for s in elig_agency.values() if s in {EligibilityState.PLAYABLE_VERIFIED, EligibilityState.PLAYABLE_WITH_LIMITATIONS}
        ),
        "agency_eligibility": dict(Counter(elig_agency.values())),
        "blocked_egress_leads": sum(1 for lead in leads if lead.acquisition_status == AcquisitionStatus.BLOCKED_EGRESS),
    }
