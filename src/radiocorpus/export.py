"""Normalized JSONL export: the hand-off format for downstream apps and for a future
PostgreSQL load. Verified and unverified material land in separate files."""

from __future__ import annotations

from pathlib import Path

from radiocorpus.models.common import VerificationStatus
from radiocorpus.store import Store, dump_jsonl


def export_all(store: Store, out_dir: Path, *, registry_filter: str | None = None, include_fixtures: bool = False) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    agencies = [a for a in store.agencies(include_fixtures=include_fixtures) if registry_filter is None or registry_filter in a.source_registry_ids]
    aid = {a.agency_id for a in agencies}
    facts = [f for f in store.facts() if f.agency_id in aid]
    counts = {
        "agencies": dump_jsonl(agencies, out_dir / "agencies.jsonl"),
        "agency_links": dump_jsonl([lk for lk in store.links() if lk.agency_id in aid], out_dir / "agency_links.jsonl"),
        "document_leads": dump_jsonl([lead for lead in store.leads() if lead.agency_id in aid], out_dir / "document_leads.jsonl"),
        "sources": dump_jsonl(
            [s for s in store.sources(include_fixtures=include_fixtures) if s.agency_or_jurisdiction in aid], out_dir / "sources.jsonl"
        ),
        "facts_verified": dump_jsonl(
            [f for f in facts if f.verification_status in {VerificationStatus.VERIFIED, VerificationStatus.CORROBORATED}],
            out_dir / "facts_verified.jsonl",
        ),
        "facts_unverified": dump_jsonl(
            [f for f in facts if f.verification_status not in {VerificationStatus.VERIFIED, VerificationStatus.CORROBORATED}],
            out_dir / "facts_unverified.jsonl",
        ),
        "conflicts": dump_jsonl([c for c in store.conflicts() if c.agency_id in aid], out_dir / "conflicts.jsonl"),
        "eligibility": dump_jsonl(
            [e for e in store.eligibility() if e.subject_id in aid or e.subject_id in {f.fact_id for f in facts}], out_dir / "eligibility.jsonl"
        ),
    }
    return counts
