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
        if e.state not in {EligibilityState.PLAYABLE_VERIFIED, EligibilityState.PLAYABLE_WITH_LIMITATIONS}:
            continue
        f = store.get_fact(e.subject_id)
        s = store.get_source(f.source_id) if f else None
        from datetime import date

        from radiocorpus.models.common import Currentness
        from radiocorpus.provenance.classify import classify_source
        from radiocorpus.provenance.evidence import (
            acquired_bytes_match,
            applicability_matches,
            currentness,
            identity_matches,
            pointer_exists,
            reviewed_fact_matches,
        )

        owner = store.get_agency(s.agency_or_jurisdiction or "") if s else None
        if (
            not f
            or not s
            or s.source_quality != SourceQuality.OFFICIAL_CURRENT
            or not owner
            or classify_source(s, owner.canonical_name, owner.state, date.today())[0] != SourceQuality.OFFICIAL_CURRENT
            or f.verification_status != VerificationStatus.VERIFIED
            or not f.excerpt
            or f.superseded_by
            or (f.effective_to and f.effective_to < date.today())
            or (f.effective_from and f.effective_from > date.today())
            or f.temporal_status != TemporalStatus.CURRENT
            or not acquired_bytes_match(store, s)
            or currentness(s) != Currentness.CONFIRMED
            or not identity_matches(s, s.agency_or_jurisdiction)
            or not pointer_exists(store, s.identity_evidence)
            or not pointer_exists(store, s.currentness_evidence)
            or not applicability_matches(store, f, s)
            or f.review_status != ReviewStatus.HUMAN_ACCEPTED
            or not reviewed_fact_matches(f, s)
        ):
            bad.append(f"{e.subject_id}: PLAYABLE_VERIFIED without OFFICIAL_CURRENT hashed source")
    return bad


def inv_no_cross_agency_synthesis(store: Store) -> list[str]:
    """Cross-entity facts require explicit dated applicability for their type and key."""
    bad = []
    for f in store.facts():
        s = store.get_source(f.source_id)
        if s is None:
            bad.append(f"{f.fact_id}: missing source")
            continue
        from radiocorpus.provenance.evidence import applicability_matches

        if s.agency_or_jurisdiction != f.agency_id and not applicability_matches(store, f, s):
            bad.append(f"{f.fact_id}: source {s.source_id} belongs to {s.agency_or_jurisdiction}, fact to {f.agency_id}")
    return bad


def inv_historical_never_overrides_current(store: Store) -> list[str]:
    """A fact from an OFFICIAL_HISTORICAL/HISTORICAL source can never be PLAYABLE_VERIFIED, and a resolved
    temporal conflict must have explicit supersession evidence."""
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
            for fid in c.fact_ids:
                f = store.get_fact(fid)
                source = store.get_source(f.source_id) if f else None
                if f and pf and f.value_fingerprint() != pf.value_fingerprint():
                    if not source or source.superseded_by != pf.source_id:
                        bad.append(f"{c.conflict_id}: temporal preference lacks explicit supersession")
    return bad


def inv_no_unreviewed_model_output_verified(store: Store) -> list[str]:
    """No evidence-free or unreviewed model output may be VERIFIED."""
    bad = []
    eligibility = {e.subject_id: e.state for e in store.eligibility("fact")}
    for f in store.facts():
        if f.verification_status == VerificationStatus.VERIFIED and (
            f.review_status != ReviewStatus.HUMAN_ACCEPTED or eligibility.get(f.fact_id) != EligibilityState.PLAYABLE_VERIFIED
        ):
            bad.append(f"{f.fact_id}: VERIFIED requires accepted review and playable eligibility")
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
        from radiocorpus.discovery.identity import verified_website

        if a.official_website and (not a.identity_evidence or not verified_website(a, a.official_website, a.identity_evidence)):
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


def inv_disagreements_block_playback(store: Store) -> list[str]:
    from collections import defaultdict

    groups = defaultdict(list)
    for fact in store.facts():
        if fact.verification_status != VerificationStatus.REJECTED:
            groups[(fact.agency_id, fact.fact_type, fact.key)].append(fact)
    playable = {
        e.subject_id for e in store.eligibility("fact") if e.state in {EligibilityState.PLAYABLE_VERIFIED, EligibilityState.PLAYABLE_WITH_LIMITATIONS}
    }
    return [
        f"{key}: disagreement cannot be playable without structured resolution evidence"
        for key, facts in groups.items()
        if len({f.value_fingerprint() for f in facts}) > 1 and any(f.fact_id in playable for f in facts)
    ]


ALL: dict[str, Callable[[Store], list[str]]] = {
    "disagreements_block_playback": inv_disagreements_block_playback,
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
