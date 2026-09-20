"""Canary report generator: one row per canary agency answering the sprint's ten questions
strictly from stored data."""

from __future__ import annotations

from pathlib import Path

from radiocorpus.models.common import AcquisitionStatus, EligibilityState, FactType, LeadClass, ResearchStatus, VerificationStatus
from radiocorpus.store import Store

QUESTIONS = [
    "agency_discovered",
    "official_domain",
    "radio_policy_source",
    "current_official_protocol_source",
    "codes",
    "phonetic",
    "procedures",
    "conflicts",
    "historical_docs",
    "training_eligibility",
]


def canary_rows(store: Store, registry: str = "CURATED_CANARY") -> list[dict]:
    rows = []
    elig = {e.subject_id: e for e in store.eligibility("agency")}
    for a in sorted(store.agencies(), key=lambda x: x.source_registry_ids.get(registry, [""])[0]):
        if registry not in a.source_registry_ids:
            continue
        leads = store.leads(a.agency_id)
        sources = store.sources(a.agency_id)
        facts = [f for f in store.facts(a.agency_id) if f.verification_status != VerificationStatus.REJECTED]
        conflicts = store.conflicts(a.agency_id)
        searched = a.research_status not in {ResearchStatus.BLOCKED, ResearchStatus.SEED_UNCONFIRMED}
        fbi = a.source_registry_ids.get("FBI_CDE_FRONTEND_2018", [])
        subunits = sum(1 for lk in store.links(agency_id=a.agency_id) if lk.link_kind == "subunit")
        radio_leads = [lead for lead in leads if lead.lead_class == LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE]
        blocked = sum(1 for lead in leads if lead.acquisition_status == AcquisitionStatus.BLOCKED_EGRESS)
        e = elig.get(a.agency_id)
        rows.append(
            {
                "canary_id": a.source_registry_ids[registry][0],
                "agency": a.canonical_name,
                "state": a.state,
                "type": a.agency_type,
                "agency_discovered": (
                    "YES (search+FBI ORI)"
                    if fbi and searched
                    else "YES (search)"
                    if searched
                    else "REGISTRY ONLY (FBI ORI)"
                    if fbi
                    else "NOT SEARCHED (budget)"
                )
                if (searched or fbi)
                else "NOT SEARCHED (budget)",
                "fbi_ori": ",".join(fbi[:3]) + (f" (+{subunits} subunits)" if subunits else ""),
                "official_domain": a.official_website or ("UNKNOWN" if searched else "NOT SEARCHED"),
                "radio_policy_source": f"LEAD x{len(radio_leads)} (not acquired: egress blocked)"
                if radio_leads
                else ("NONE FOUND IN SEARCH" if searched else "NOT SEARCHED"),
                "current_official_protocol_source": "UNKNOWN (no document acquired)"
                if not sources
                else f"{sum(1 for s in sources if s.source_quality == 'OFFICIAL_CURRENT')} current official",
                "codes": _fact_summary(facts, FactType.CODE_MEANING),
                "phonetic": _fact_summary(facts, FactType.PHONETIC_LETTER),
                "procedures": _fact_summary(facts, FactType.PROCEDURE_RULE),
                "conflicts": str(len(conflicts)) if conflicts else "none (no extracted facts to compare)",
                "historical_docs": str(sum(1 for s in sources if s.source_quality == "OFFICIAL_HISTORICAL")) if sources else "UNKNOWN",
                "training_eligibility": e.state if e else EligibilityState.INSUFFICIENT_EVIDENCE,
                "leads_blocked_egress": blocked,
                "research_status": a.research_status,
                "top_radio_leads": [f"{lead.title} <{lead.url}>" for lead in radio_leads[:3]],
            }
        )
    return rows


def _fact_summary(facts, ftype) -> str:  # type: ignore[no-untyped-def]
    n = sum(1 for f in facts if f.fact_type == ftype)
    return f"{n} candidate(s)" if n else "NOT DISCOVERED (no acquired document)"


def render_markdown(store: Store, registry: str = "CURATED_CANARY", preamble: Path | None = None) -> str:
    """Generate identity statements from exactly the records eligible for export."""
    from radiocorpus.report_consistency import identity_report

    agencies = [a.model_dump(mode="json") for a in store.agencies() if registry in a.source_registry_ids]
    return identity_report(agencies)
