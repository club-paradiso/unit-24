"""Stage 9+10: cross-check and conflict detection.

For each (agency, fact_type, key) with facts from more than one source, compare value
fingerprints. Different values => a Conflict. Resolution is attempted ONLY with evidence:
  * temporal: both sources official and dated, one strictly newer => newer preferred, the
    older source's facts are marked HISTORICAL (never deleted, never demoted to rejected);
  * quality: official vs non-official => official preferred (secondary kept as UNVERIFIED);
  * jurisdictional: agency's own policy vs dispatch-centre/parent doc => agency's own preferred.
Otherwise UNRESOLVED. Undated official vs official => UNDATED_MANUAL, unresolved.
Nothing here ever infers a value for an agency from another agency's facts."""

from __future__ import annotations

from collections import Counter, defaultdict

from radiocorpus import ids
from radiocorpus.models import Conflict, ProtocolFact, Source, StageRun
from radiocorpus.models.common import ConflictKind, ConflictResolution, SourceType, TemporalStatus, VerificationStatus
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.store import Store


def _kind(sa: Source, sb: Source) -> ConflictKind:
    if sa.is_official and sb.is_official:
        if sa.temporal_status != sb.temporal_status and TemporalStatus.HISTORICAL in (sa.temporal_status, sb.temporal_status):
            return ConflictKind.CURRENT_VS_OBSOLETE
        types = {sa.source_type, sb.source_type}
        if SourceType.DISPATCH_CENTER_DOCUMENT in types and SourceType.AGENCY_POLICY_MANUAL in types:
            return ConflictKind.AGENCY_VS_DISPATCH
        if (sa.effective_date or sa.publication_date) is None or (sb.effective_date or sb.publication_date) is None:
            return ConflictKind.UNDATED_MANUAL
        return ConflictKind.OFFICIAL_VS_OFFICIAL
    if sa.is_official != sb.is_official:
        return ConflictKind.SECONDARY_VS_OFFICIAL
    return ConflictKind.SECONDARY_VS_SECONDARY


def _date(s: Source):  # type: ignore[no-untyped-def]
    return s.effective_date or s.publication_date


def detect_conflicts(store: Store) -> StageRun:
    facts = [f for f in store.facts() if f.verification_status != VerificationStatus.REJECTED]
    run = start_run(store, "conflicts", str(len(facts)))
    stats: Counter[str] = Counter()
    groups: dict[tuple[str, str, str], list[ProtocolFact]] = defaultdict(list)
    for f in facts:
        groups[(f.agency_id, f.fact_type, f.key)].append(f)
    src_cache: dict[str, Source] = {}

    def src(sid: str) -> Source:
        if sid not in src_cache:
            s = store.get_source(sid)
            if s is None:
                raise KeyError(sid)
            src_cache[sid] = s
        return src_cache[sid]

    with store.tx():
        for (agency_id, ftype, key), grp in groups.items():
            by_value: dict[str, list[ProtocolFact]] = defaultdict(list)
            for f in grp:
                by_value[f.value_fingerprint()].append(f)
            if len(by_value) < 2:
                continue
            fact_ids = sorted(f.fact_id for f in grp)
            source_ids = sorted({f.source_id for f in grp})
            cid = ids.conflict_id(agency_id, ftype, key, fact_ids)
            existing = {c.conflict_id: c for c in store.conflicts(agency_id)}
            if cid in existing and existing[cid].resolution == ConflictResolution.RESOLVED_HUMAN:
                stats["kept_human_resolution"] += 1
                continue
            # pairwise kind: take the "strongest" pair classification across distinct values
            reps = [v[0] for v in by_value.values()]
            kinds = [_kind(src(a.source_id), src(b.source_id)) for i, a in enumerate(reps) for b in reps[i + 1 :]]
            kind = kinds[0] if len(set(kinds)) == 1 else ConflictKind.OTHER
            resolution, preferred, rationale = _try_resolve(reps, src)
            c = Conflict(
                conflict_id=cid,
                agency_id=agency_id,
                fact_type=ftype,
                key=key,
                fact_ids=fact_ids,
                source_ids=source_ids,
                kind=kind,
                resolution=resolution,
                preferred_fact_id=preferred,
                rationale=rationale,
                run_id=run.run_id,
            )
            store.upsert_conflict(c)
            stats[f"conflict:{kind}"] += 1
            stats[f"resolution:{resolution}"] += 1
            if resolution == ConflictResolution.RESOLVED_TEMPORAL and preferred:
                pref_fp = store.get_fact(preferred).value_fingerprint()  # type: ignore[union-attr]
                for f in grp:
                    if f.fact_id != preferred and f.value_fingerprint() != pref_fp and src(f.source_id).is_official:
                        store.record_fact_status(
                            f.fact_id,
                            temporal_status=TemporalStatus.HISTORICAL,
                            superseded_by=preferred,
                            reason=f"conflict {cid}: superseded by newer dated official source",
                            run_id=run.run_id,
                        )
    return finish_run(store, run, dict(stats))


def _try_resolve(reps: list[ProtocolFact], src) -> tuple[ConflictResolution, str | None, str]:  # type: ignore[no-untyped-def]
    officials = [f for f in reps if src(f.source_id).is_official]
    if len(officials) == 1 and len(reps) > 1:
        return (
            ConflictResolution.RESOLVED_QUALITY,
            officials[0].fact_id,
            "single official source outranks non-official sources; non-official facts retained as UNVERIFIED",
        )
    if len(officials) >= 2:
        own = [f for f in officials if src(f.source_id).source_type == SourceType.AGENCY_POLICY_MANUAL]
        others = [f for f in officials if f not in own]
        if (
            len(own) == 1
            and others
            and all(src(o.source_id).source_type in {SourceType.DISPATCH_CENTER_DOCUMENT, SourceType.GOVERNMENT_DOCUMENT} for o in others)
        ):
            return (
                ConflictResolution.RESOLVED_JURISDICTIONAL,
                own[0].fact_id,
                "agency's own policy manual outranks dispatch-centre/parent-government documents for agency-specific usage",
            )
        dated = [(d, f) for f in officials if (d := _date(src(f.source_id))) is not None]
        if len(dated) == len(officials):
            dated.sort(key=lambda x: x[0], reverse=True)
            if len(dated) == 1 or dated[0][0] > dated[1][0]:
                return (
                    ConflictResolution.RESOLVED_TEMPORAL,
                    dated[0][1].fact_id,
                    f"newest dated official source ({dated[0][0]}) supersedes older ({dated[1][0]})",
                )
            return ConflictResolution.UNRESOLVED, None, "two official sources share the same date and disagree"
        return ConflictResolution.UNRESOLVED, None, "official sources disagree and at least one is undated; cannot order them"
    return ConflictResolution.UNRESOLVED, None, "no official source among conflicting values; nothing to prefer"
