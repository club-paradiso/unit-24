"""Stages 3+4: official-domain discovery and document discovery from search hits.

Official website is set on the agency only when a hit satisfies ALL of:
  * host judged official (government TLD or state-government host), and
  * the result title mentions the agency (core-token overlap), and
  * it came from the agency's own "official website" query (search index A) or the host is
    agency-branded (.gov with agency tokens).
Anything weaker is recorded as a lead; the website field stays None (UNKNOWN).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from radiocorpus import ids
from radiocorpus.discovery.classify import classify_hit, title_mentions_agency
from radiocorpus.discovery.providers import RecordedSearchProvider, SearchNotPerformed
from radiocorpus.models import Agency, DocumentLead, StageRun
from radiocorpus.models.common import AcquisitionStatus, LeadClass, ResearchStatus, utcnow
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.registry.ingest import file_fingerprint
from radiocorpus.store import Store


def _canary_agencies(store: Store, registry: str) -> dict[str, Agency]:
    out: dict[str, Agency] = {}
    for a in store.agencies():
        for ext in a.source_registry_ids.get(registry, []):
            out[ext] = a
    return out


def discover_from_recorded(store: Store, leads_path: Path, *, registry: str = "CURATED_CANARY", force: bool = False) -> StageRun:
    prov = RecordedSearchProvider(leads_path)
    fp = file_fingerprint(leads_path)
    run = start_run(store, "discovery", fp)
    agencies = _canary_agencies(store, registry)
    stats: Counter[str] = Counter()
    with store.tx():
        for ext, a in sorted(agencies.items()):
            if not force and store.progress_done("discovery", a.agency_id, fp):
                stats["skipped_resumed"] += 1
                continue
            hits = prov.hits_for_subject(ext)
            blocked = prov.not_performed(ext)
            judgment = prov.judgment(ext)
            if not hits and not blocked and judgment is not None:
                # a worker looked at this agency but recorded no searches: treat as not performed, never as "no results"
                blocked = [
                    SearchNotPerformed(
                        query="",
                        subject_key=ext,
                        search_index=None,
                        retrieved_at=utcnow(),
                        engine=prov.engine,
                        reason=f"no search recorded; worker note: {str(judgment.get('notes', ''))[:160]}",
                    )
                ]
            website: str | None = None
            website_basis: str | None = None
            classes: Counter[str] = Counter()
            for h in hits:
                lc, hj, basis = classify_hit(h.url, h.title, h.snippet, a.canonical_name, a.state)
                classes[lc] += 1
                lead = DocumentLead(
                    lead_id=ids.lead_id(a.agency_id, h.url, h.query),
                    agency_id=a.agency_id,
                    url=h.url,
                    host=hj.host,
                    title=h.title,
                    snippet=h.snippet,
                    discovered_via=f"search_engine:{h.engine}",
                    query=h.query,
                    rank=h.rank,
                    retrieved_at=h.retrieved_at,
                    lead_class=lc,
                    classification_basis=f"{basis}; host: {hj.basis}",
                    host_is_official=hj.is_official,
                    acquisition_status=AcquisitionStatus.PENDING if lc != LeadClass.UNRELATED else AcquisitionStatus.SKIPPED_NOT_CANDIDATE,
                )
                store.upsert_lead(lead)
                stats["leads"] += 1
                if website is None and hj.is_official and h.search_index == "A" and title_mentions_agency(h.title, a.canonical_name):
                    website = h.url
                    website_basis = f"search A rank {h.rank}: title {h.title!r} on {hj.host}"
            searched = bool(hits)
            if searched:
                if website:
                    status = ResearchStatus.DOMAIN_DISCOVERED
                    stats["website_set"] += 1
                else:
                    status = ResearchStatus.DISCOVERY_STARTED
                if classes[LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE] or classes[LeadClass.OFFICIAL_DOCUMENT_CANDIDATE]:
                    status = ResearchStatus.DOCUMENTS_DISCOVERED
                    stats["docs_discovered"] += 1
            elif blocked:
                status = ResearchStatus.BLOCKED
                stats["blocked_no_search"] += 1
            else:
                status = ResearchStatus.SEED_UNCONFIRMED
            notes = a.notes or ""
            if blocked:
                notes = (notes + "; " if notes else "") + f"{len(blocked)} search(es) not performed: {blocked[0].reason}"
            if website_basis:
                notes = (notes + "; " if notes else "") + f"website basis: {website_basis}"
            a2 = a.model_copy(
                update={
                    "official_website": website or a.official_website,
                    "research_status": status,
                    "last_verified": utcnow() if searched else a.last_verified,
                    "notes": notes or None,
                }
            )
            store.upsert_agency(a2)
            store.mark_progress("discovery", a.agency_id, fp, "done", run.run_id, note=str(status))
            stats["agencies"] += 1
    return finish_run(store, run, dict(stats))
