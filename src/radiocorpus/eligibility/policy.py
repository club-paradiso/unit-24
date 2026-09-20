"""Reviewed, current, entity-matched official evidence is required for playback.

No parser is eligible for automatic verification. Corroboration requires distinct
URL, hash, issuer and known disjoint lineage, and remains research-only. Expired,
superseded, unresolved and unreviewed facts cannot become learner expectations.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from radiocorpus.models import EligibilityDecision, ProtocolFact, Source, StageRun
from radiocorpus.models.common import (
    ConflictResolution,
    Currentness,
    EligibilityState,
    ReviewStatus,
    SourceQuality,
    TemporalStatus,
    VerificationStatus,
)
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.provenance.evidence import (
    acquired_bytes_match,
    applicability_matches,
    currentness,
    identity_matches,
    independently_corroborated,
    pointer_exists,
    reviewed_fact_matches,
)
from radiocorpus.store import Store

POLICY_VERSION = "2026-09-20.2"
_RANK = [
    EligibilityState.PLAYABLE_VERIFIED,
    EligibilityState.PLAYABLE_WITH_LIMITATIONS,
    EligibilityState.HISTORICAL_ONLY,
    EligibilityState.CONFLICT_REQUIRES_REVIEW,
    EligibilityState.RESEARCH_ONLY,
    EligibilityState.INSUFFICIENT_EVIDENCE,
]


def decide_fact(
    f: ProtocolFact, src: Source, unresolved_conflicts: list[str], losing: tuple[str, str] | None, corroborated: bool
) -> tuple[VerificationStatus, EligibilityDecision]:
    if f.verification_status == VerificationStatus.REJECTED or f.review_status == ReviewStatus.HUMAN_REJECTED:
        return f.verification_status, _dec(
            f, EligibilityState.INSUFFICIENT_EVIDENCE, ["fact rejected by validation or human review"], src, unresolved_conflicts
        )
    if unresolved_conflicts:
        return VerificationStatus.UNVERIFIED, _dec(
            f, EligibilityState.CONFLICT_REQUIRES_REVIEW, [f"unresolved conflict(s): {', '.join(unresolved_conflicts)}"], src, unresolved_conflicts
        )
    from datetime import date

    if f.source_id != src.source_id or f.superseded_by or (f.effective_to and f.effective_to < date.today()):
        return VerificationStatus.UNVERIFIED, _dec(f, EligibilityState.RESEARCH_ONLY, ["source mismatch or expired/superseded fact"], src, [])
    if f.effective_from and f.effective_from > date.today():
        return VerificationStatus.UNVERIFIED, _dec(f, EligibilityState.RESEARCH_ONLY, ["fact is not yet effective"], src, [])
    # No parser has yet earned an auto-verification allowlist entry on real data.
    # ExtractionMethod.HUMAN alone also does not establish a completed review.
    if f.review_status != ReviewStatus.HUMAN_ACCEPTED or not reviewed_fact_matches(f, src):
        return VerificationStatus.UNVERIFIED, _dec(
            f, EligibilityState.RESEARCH_ONLY, ["parser output requires independent acceptance; no validated auto-verification rule"], src, []
        )
    if losing:
        return VerificationStatus.UNVERIFIED, _dec(
            f, EligibilityState.RESEARCH_ONLY, ["conflicting value is not the preferred evidence"], src, [losing[0]]
        )
    status = currentness(src)
    if status in {Currentness.HISTORICAL, Currentness.SUPERSEDED} or f.temporal_status == TemporalStatus.HISTORICAL:
        return VerificationStatus.UNVERIFIED, _dec(f, EligibilityState.HISTORICAL_ONLY, ["historical evidence retained"], src, [])
    if (
        f.temporal_status == TemporalStatus.CURRENT
        and src.source_quality == SourceQuality.OFFICIAL_CURRENT
        and status == Currentness.CONFIRMED
        and identity_matches(src, src.agency_or_jurisdiction)
        and f.excerpt
    ):
        return VerificationStatus.VERIFIED, _dec(
            f, EligibilityState.PLAYABLE_VERIFIED, ["reviewed fact with explicit identity and currentness evidence"], src, []
        )
    return VerificationStatus.CORROBORATED if corroborated else VerificationStatus.UNVERIFIED, _dec(
        f, EligibilityState.RESEARCH_ONLY, ["current authoritative evidence not established; repetition cannot grant eligibility"], src, []
    )


def _dec(f: ProtocolFact, state: EligibilityState, reasons: list[str], src: Source, conflicts: list[str]) -> EligibilityDecision:
    return EligibilityDecision(
        subject_kind="fact",
        subject_id=f.fact_id,
        state=state,
        reasons=reasons,
        supporting_source_ids=[src.source_id],
        conflict_ids=conflicts,
        policy_version=POLICY_VERSION,
    )


def assign_all(store: Store) -> StageRun:
    from radiocorpus.conflicts.detect import detect_conflicts

    detect_conflicts(store)  # newly appended facts cannot bypass a stale conflict table
    facts = store.facts()
    run = start_run(store, "eligibility", str(len(facts)))
    stats: Counter[str] = Counter()
    conflicts = store.conflicts()
    unresolved_by_fact: dict[str, list[str]] = defaultdict(list)
    losing: dict[str, tuple[str, str]] = {}
    for c in conflicts:
        if c.resolution == ConflictResolution.UNRESOLVED:
            for fid in c.fact_ids:
                unresolved_by_fact[fid].append(c.conflict_id)
        elif c.preferred_fact_id:
            pref = store.get_fact(c.preferred_fact_id)
            for fid in c.fact_ids:
                f = store.get_fact(fid)
                if f and pref and f.value_fingerprint() != pref.value_fingerprint():
                    losing[fid] = (c.conflict_id, str(c.resolution))
    # Group equal candidates, then require documented independence below.
    by_val: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for f in facts:
        by_val[(f.agency_id, f.fact_type, f.key, f.value_fingerprint())].add(f.source_id)
    agency_states: dict[str, list[EligibilityState]] = defaultdict(list)
    with store.tx():
        for f in facts:
            src = store.get_source(f.source_id)
            if src is None:
                continue
            peers = [store.get_source(sid) for sid in by_val[(f.agency_id, f.fact_type, f.key, f.value_fingerprint())]]
            corroborated = independently_corroborated([s for s in peers if s])
            vs, dec = decide_fact(f, src, unresolved_by_fact.get(f.fact_id, []), losing.get(f.fact_id), corroborated)
            from datetime import date

            from radiocorpus.provenance.classify import classify_source

            owner = store.get_agency(src.agency_or_jurisdiction or "")
            if dec.state in {EligibilityState.PLAYABLE_VERIFIED, EligibilityState.PLAYABLE_WITH_LIMITATIONS} and (
                not owner
                or classify_source(src, owner.canonical_name, owner.state, date.today())[0] != SourceQuality.OFFICIAL_CURRENT
                or not acquired_bytes_match(store, src)
                or not applicability_matches(store, f, src)
                or not (pointer_exists(store, src.identity_evidence) and pointer_exists(store, src.currentness_evidence))
            ):
                vs = VerificationStatus.UNVERIFIED
                dec = _dec(f, EligibilityState.RESEARCH_ONLY, ["missing scoped applicability or evidence source"], src, [])
            if vs != f.verification_status:
                store.record_fact_status(
                    f.fact_id,
                    verification_status=vs,
                    review_status=ReviewStatus.AUTO_ACCEPTED
                    if vs == VerificationStatus.VERIFIED and f.review_status == ReviewStatus.UNREVIEWED
                    else None,
                    reason=f"eligibility policy {POLICY_VERSION}: {dec.reasons[0]}",
                    run_id=run.run_id,
                )
            store.upsert_eligibility(dec)
            agency_states[f.agency_id].append(dec.state)
            stats[f"fact:{dec.state}"] += 1
        for a in store.agencies(include_fixtures=True):
            states = agency_states.get(a.agency_id, [])
            if states:
                best = min(states, key=_RANK.index)
                reasons = [f"best fact state among {len(states)} facts"]
            else:
                best = EligibilityState.INSUFFICIENT_EVIDENCE
                reasons = ["no protocol facts with evidence"]
            store.upsert_eligibility(
                EligibilityDecision(subject_kind="agency", subject_id=a.agency_id, state=best, reasons=reasons, policy_version=POLICY_VERSION)
            )
            stats[f"agency:{best}"] += 1
    return finish_run(store, run, dict(stats))


def explain(store: Store, fact_id: str) -> dict:
    """Answer 'why is this the expected answer?' strictly from stored evidence."""
    f = store.get_fact(fact_id)
    if f is None:
        raise KeyError(fact_id)
    src = store.get_source(f.source_id)
    dec = next((e for e in store.eligibility("fact") if e.subject_id == fact_id), None)
    return {
        "fact_id": f.fact_id,
        "agency_id": f.agency_id,
        "fact_type": f.fact_type,
        "key": f.key,
        "value": f.value.model_dump(),
        "excerpt": f.excerpt,
        "locator": f.locator,
        "source": {
            "source_id": src.source_id,
            "title": src.title,
            "url": src.canonical_url,
            "document_hash": src.document_hash,
            "quality": src.source_quality,
            "effective_date": str(src.effective_date) if src.effective_date else None,
        }
        if src
        else None,
        "verification_status": f.verification_status,
        "extraction_method": f.extraction_method,
        "extraction_model": f.extraction_model,
        "eligibility": dec.state if dec else None,
        "eligibility_reasons": dec.reasons if dec else [],
        "conflicts": dec.conflict_ids if dec else [],
    }
