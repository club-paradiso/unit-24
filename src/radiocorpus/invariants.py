"""Corpus invariants. Each returns a list of violation strings; empty means it holds.
They are run by `radiocorpus check-invariants` and by the test-suite."""

from __future__ import annotations

from collections.abc import Callable

from radiocorpus.models.common import (
    EligibilityState,
    ExtractionMethod,
    ReviewStatus,
    SourceQuality,
    SourceType,
    TemporalStatus,
    VerificationStatus,
)
from radiocorpus.store import Store


def inv_playable_requires_official_evidence(store: Store) -> list[str]:
    """No PLAYABLE_VERIFIED fact may exist without at least one qualifying (OFFICIAL_CURRENT, hashed) source."""
    bad = []
    for e in store.eligibility("fact"):
        if e.state != EligibilityState.PLAYABLE_VERIFIED:
            continue
        f = store.get_fact(e.subject_id)
        s = store.get_source(f.source_id) if f else None
        if not f or not s or s.source_quality != SourceQuality.OFFICIAL_CURRENT or not s.document_hash:
            bad.append(f"{e.subject_id}: PLAYABLE_VERIFIED without OFFICIAL_CURRENT hashed source")
    return bad


def inv_no_cross_agency_synthesis(store: Store) -> list[str]:
    """Every fact's source must be attributed to the fact's own agency (or its documented parent/dispatch provider).
    A fact can never cite a neighbouring agency's document."""
    bad = []
    for f in store.facts():
        s = store.get_source(f.source_id)
        if s is None:
            bad.append(f"{f.fact_id}: missing source")
            continue
        a = store.get_agency(f.agency_id)
        allowed = {f.agency_id}
        if a and a.parent_agency:
            allowed.add(a.parent_agency)
        if a and a.dispatch_provider and a.dispatch_provider.startswith("agy_"):
            allowed.add(a.dispatch_provider)
        if s.agency_or_jurisdiction not in allowed:
            bad.append(f"{f.fact_id}: source {s.source_id} belongs to {s.agency_or_jurisdiction}, fact to {f.agency_id}")
    return bad


def inv_historical_never_overrides_current(store: Store) -> list[str]:
    """A fact from an OFFICIAL_HISTORICAL/HISTORICAL source can never be PLAYABLE_VERIFIED, and a resolved
    temporal conflict must prefer the newer-dated source."""
    bad = []
    elig = {e.subject_id: e.state for e in store.eligibility("fact")}
    for f in store.facts():
        s = store.get_source(f.source_id)
        if s and (s.source_quality == SourceQuality.OFFICIAL_HISTORICAL or f.temporal_status == TemporalStatus.HISTORICAL):
            if elig.get(f.fact_id) == EligibilityState.PLAYABLE_VERIFIED:
                bad.append(f"{f.fact_id}: historical fact marked PLAYABLE_VERIFIED")
    for c in store.conflicts():
        if c.resolution == "resolved_temporal" and c.preferred_fact_id:
            pf = store.get_fact(c.preferred_fact_id)
            ps = store.get_source(pf.source_id) if pf else None
            pd = (ps.effective_date or ps.publication_date) if ps else None
            for fid in c.fact_ids:
                f = store.get_fact(fid)
                s = store.get_source(f.source_id) if f else None
                d = (s.effective_date or s.publication_date) if s else None
                if d and pd and d > pd:
                    bad.append(f"{c.conflict_id}: preferred source older than a competing source")
    return bad


def inv_no_unreviewed_model_output_verified(store: Store) -> list[str]:
    """No evidence-free or unreviewed model output may be VERIFIED."""
    bad = []
    for f in store.facts():
        if (
            f.extraction_method == ExtractionMethod.MODEL
            and f.verification_status == VerificationStatus.VERIFIED
            and f.review_status != ReviewStatus.HUMAN_ACCEPTED
        ):
            bad.append(f"{f.fact_id}: model output VERIFIED without human acceptance")
        if not f.excerpt and f.verification_status == VerificationStatus.VERIFIED:
            bad.append(f"{f.fact_id}: VERIFIED without excerpt")
    return bad


def inv_conflicts_preserve_all_facts(store: Store) -> list[str]:
    bad = []
    for c in store.conflicts():
        for fid in c.fact_ids:
            if store.get_fact(fid) is None:
                bad.append(f"{c.conflict_id}: participating fact {fid} missing (facts must never be deleted)")
    return bad


def inv_unknown_stays_unknown(store: Store) -> list[str]:
    """official_website may only be set with a recorded basis; dispatch_provider/parent must not be
    filled for REGISTRY_ONLY agencies (nothing was researched)."""
    bad = []
    for a in store.agencies(include_fixtures=True):
        if a.official_website and "website basis:" not in (a.notes or ""):
            bad.append(f"{a.agency_id}: official_website set without basis note")
        if a.research_status == "registry_only" and (a.dispatch_provider or a.parent_agency or a.official_website):
            bad.append(f"{a.agency_id}: REGISTRY_ONLY agency carries researched fields")
    return bad


def inv_sources_official_only_when_hashed(store: Store) -> list[str]:
    bad = []
    for s in store.sources():
        if s.is_official and not s.document_hash:
            bad.append(f"{s.source_id}: official quality without document hash")
        if s.source_type in {SourceType.ENTHUSIAST_OR_CROWDSOURCED, SourceType.SOCIAL_MEDIA, SourceType.SEARCH_ENGINE_RESULT} and s.is_official:
            bad.append(f"{s.source_id}: non-official source type with official quality")
    return bad


def inv_facts_have_locators_and_sources(store: Store) -> list[str]:
    return [f"{f.fact_id}: no locator" for f in store.facts() if not f.locator] + [
        f"{f.fact_id}: dangling source {f.source_id}" for f in store.facts() if store.get_source(f.source_id) is None
    ]


ALL: dict[str, Callable[[Store], list[str]]] = {
    "playable_requires_official_evidence": inv_playable_requires_official_evidence,
    "no_cross_agency_synthesis": inv_no_cross_agency_synthesis,
    "historical_never_overrides_current": inv_historical_never_overrides_current,
    "no_unreviewed_model_output_verified": inv_no_unreviewed_model_output_verified,
    "conflicts_preserve_all_facts": inv_conflicts_preserve_all_facts,
    "unknown_stays_unknown": inv_unknown_stays_unknown,
    "sources_official_only_when_hashed": inv_sources_official_only_when_hashed,
    "facts_have_locators_and_sources": inv_facts_have_locators_and_sources,
}


def check_all(store: Store) -> dict[str, list[str]]:
    return {name: fn(store) for name, fn in ALL.items()}
