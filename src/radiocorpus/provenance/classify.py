"""Classify acquired evidence using reviewed identity and explicit currentness.

Document age and search ranking never establish operative status. Historical
and superseded evidence remains stored. Legacy quality labels are derived only.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

from radiocorpus.models import Source, StageRun
from radiocorpus.models.common import Currentness, SourceQuality, SourceType, TemporalStatus
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.provenance.evidence import currentness, identity_matches
from radiocorpus.store import Store

OFFICIAL_TYPES = {
    SourceType.AGENCY_POLICY_MANUAL,
    SourceType.DISPATCH_CENTER_DOCUMENT,
    SourceType.GOVERNMENT_DOCUMENT,
    SourceType.TRAINING_ACCREDITATION,
    SourceType.OTHER_GOVERNMENT_RECORD,
    SourceType.STANDARDS_BODY,
}


def classify_source(src: Source, agency_name: str, state: str | None, today: date) -> tuple[SourceQuality, TemporalStatus, str]:
    if not src.document_hash or src.source_type not in OFFICIAL_TYPES:
        return SourceQuality.UNVERIFIED, TemporalStatus.UNCERTAIN, "unacquired or non-official source type"
    if not identity_matches(src, src.agency_or_jurisdiction):
        return SourceQuality.UNVERIFIED, TemporalStatus.UNCERTAIN, "issuing agency identity not verified"
    if src.identity_evidence.canonical_name != agency_name or src.identity_evidence.state != state:
        return SourceQuality.UNVERIFIED, TemporalStatus.UNCERTAIN, "identity evidence conflicts with registry"
    status = currentness(src, today)
    if status in {Currentness.SUPERSEDED, Currentness.HISTORICAL}:
        return SourceQuality.OFFICIAL_HISTORICAL, TemporalStatus.HISTORICAL, str(status)
    if status == Currentness.CONFIRMED:
        return SourceQuality.OFFICIAL_CURRENT, TemporalStatus.CURRENT, "explicit currentness evidence"
    return SourceQuality.OFFICIAL_PARTIAL, TemporalStatus.UNCERTAIN, str(status)


def classify_all(store: Store, today: date | None = None) -> StageRun:
    today = today or date.today()
    sources = store.sources()
    run = start_run(store, "source_classification", str(len(sources)))
    stats: Counter[str] = Counter()
    with store.tx():
        for s in sources:
            a = store.get_agency(s.agency_or_jurisdiction or "")
            status = currentness(s, today)
            if status != s.currentness:
                store.update_source_status(
                    s.source_id, field="currentness", new_value=status, reason="explicit evidence policy v2", run_id=run.run_id
                )
            q, t, why = classify_source(s, a.canonical_name if a else "", a.state if a else None, today)
            if q != s.source_quality:
                store.update_source_status(s.source_id, field="source_quality", new_value=q, reason=why, run_id=run.run_id)
            if t != s.temporal_status:
                store.update_source_status(s.source_id, field="temporal_status", new_value=t, reason=why, run_id=run.run_id)
            stats[q] += 1
    return finish_run(store, run, dict(stats))
