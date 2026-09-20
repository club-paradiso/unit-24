"""Stage 11: confidence/verification assignment and training eligibility.

Fact-level:
  VERIFIED   := passed validation AND source OFFICIAL_CURRENT AND (deterministic extraction or human accepted)
                AND not part of an unresolved conflict AND not the losing side of a resolved conflict.
  CORROBORATED := not VERIFIED, but the same normalized value appears in >=2 independent sources.
Eligibility (fact):
  PLAYABLE_VERIFIED           VERIFIED + temporal CURRENT
  PLAYABLE_WITH_LIMITATIONS   source OFFICIAL_PARTIAL (undated/old) or CORROBORATED, no unresolved conflict
  HISTORICAL_ONLY             temporal HISTORICAL or source OFFICIAL_HISTORICAL
  CONFLICT_REQUIRES_REVIEW    participates in an unresolved conflict
  RESEARCH_ONLY               UNVERIFIED (non-official only, or model-extracted without human acceptance)
  INSUFFICIENT_EVIDENCE       REJECTED, or no evidence
Eligibility (agency): best state among its facts; INSUFFICIENT_EVIDENCE if none.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from radiocorpus.models import EligibilityDecision, ProtocolFact, Source, StageRun
from radiocorpus.models.common import (
    ConflictResolution,
    EligibilityState,
    ExtractionMethod,
    ReviewStatus,
    SourceQuality,
    TemporalStatus,
    VerificationStatus,
)
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.store import Store

POLICY_VERSION = "2026-09-20.1"
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
    reasons: list[str] = []
    if f.verification_status == VerificationStatus.REJECTED or f.review_status == ReviewStatus.HUMAN_REJECTED:
        return f.verification_status, _dec(
            f, EligibilityState.INSUFFICIENT_EVIDENCE, ["fact rejected by validation or human review"], src, unresolved_conflicts
        )
    if unresolved_conflicts:
        return VerificationStatus.UNVERIFIED, _dec(
            f, EligibilityState.CONFLICT_REQUIRES_REVIEW, [f"unresolved conflict(s): {', '.join(unresolved_conflicts)}"], src, unresolved_conflicts
        )
    human_ok = f.review_status == ReviewStatus.HUMAN_ACCEPTED
    method_ok = f.extraction_method in {ExtractionMethod.DETERMINISTIC_PARSER, ExtractionMethod.HUMAN} or human_ok
    if not method_ok:
        reasons.append("model-extracted candidate without human acceptance")
        return VerificationStatus.UNVERIFIED, _dec(f, EligibilityState.RESEARCH_ONLY, reasons, src, [])
    if losing and not (src.is_official and losing[1] == ConflictResolution.RESOLVED_TEMPORAL):
        # contradicted by the preferred source (quality or jurisdiction resolution): not historical, just not usable
        reasons.append(f"contradicted by preferred source in conflict {losing[0]} ({losing[1]})")
        return VerificationStatus.UNVERIFIED, _dec(f, EligibilityState.RESEARCH_ONLY, reasons, src, [losing[0]])
    if losing or f.temporal_status == TemporalStatus.HISTORICAL or src.source_quality == SourceQuality.OFFICIAL_HISTORICAL:
        reasons.append("superseded by a newer dated official source" if losing else "historical evidence")
        return VerificationStatus.VERIFIED if src.is_official else VerificationStatus.UNVERIFIED, _dec(
            f, EligibilityState.HISTORICAL_ONLY, reasons, src, [losing[0]] if losing else []
        )
    if src.source_quality == SourceQuality.OFFICIAL_CURRENT:
        reasons.append(f"official current source {src.source_id} ({src.canonical_url})")
        return VerificationStatus.VERIFIED, _dec(f, EligibilityState.PLAYABLE_VERIFIED, reasons, src, [])
    if src.source_quality == SourceQuality.OFFICIAL_PARTIAL:
        reasons.append("official source without a usable effective date (or older than the currency window)")
        return VerificationStatus.VERIFIED, _dec(f, EligibilityState.PLAYABLE_WITH_LIMITATIONS, reasons, src, [])
    if corroborated:
        reasons.append("value corroborated by >=2 independent sources, none official-current")
        return VerificationStatus.CORROBORATED, _dec(f, EligibilityState.PLAYABLE_WITH_LIMITATIONS, reasons, src, [])
    reasons.append(f"source quality {src.source_quality}; not usable for training")
    return VerificationStatus.UNVERIFIED, _dec(f, EligibilityState.RESEARCH_ONLY, reasons, src, [])


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
    # corroboration: same (agency, type, key, value) from >=2 distinct sources
    by_val: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for f in facts:
        by_val[(f.agency_id, f.fact_type, f.key, f.value_fingerprint())].add(f.source_id)
    agency_states: dict[str, list[EligibilityState]] = defaultdict(list)
    with store.tx():
        for f in facts:
            src = store.get_source(f.source_id)
            if src is None:
                continue
            corroborated = len(by_val[(f.agency_id, f.fact_type, f.key, f.value_fingerprint())]) >= 2
            vs, dec = decide_fact(f, src, unresolved_by_fact.get(f.fact_id, []), losing.get(f.fact_id), corroborated)
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
