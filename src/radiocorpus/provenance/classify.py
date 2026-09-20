"""Source quality and temporal classification.

Quality is assigned from (a) what kind of host the document came from, (b) whether we hold
the bytes (hash), and (c) whether a newer official source for the same agency + subject
supersedes it. An undated official document is OFFICIAL_PARTIAL, never OFFICIAL_CURRENT: we
cannot claim currency without a date or an explicit "current" marker on an official page.

Rules are deliberately conservative; a human may upgrade via update_source_status with a reason.
"""

from __future__ import annotations

from collections import Counter
from datetime import date

from radiocorpus.discovery.classify import judge_host
from radiocorpus.models import Source, StageRun
from radiocorpus.models.common import SourceQuality, SourceType, TemporalStatus
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.store import Store

OFFICIAL_TYPES = {
    SourceType.AGENCY_POLICY_MANUAL,
    SourceType.DISPATCH_CENTER_DOCUMENT,
    SourceType.GOVERNMENT_DOCUMENT,
    SourceType.TRAINING_ACCREDITATION,
    SourceType.OTHER_GOVERNMENT_RECORD,
    SourceType.STANDARDS_BODY,
}
CURRENT_WINDOW_YEARS = 10  # a dated official document older than this is not presumed current


def classify_source(src: Source, agency_name: str, state: str | None, today: date) -> tuple[SourceQuality, TemporalStatus, str]:
    if src.document_hash is None:
        return SourceQuality.UNVERIFIED, TemporalStatus.UNCERTAIN, "not acquired"
    if src.source_type in {SourceType.ENTHUSIAST_OR_CROWDSOURCED, SourceType.SOCIAL_MEDIA, SourceType.SEARCH_ENGINE_RESULT}:
        return SourceQuality.UNVERIFIED, TemporalStatus.UNCERTAIN, "non-official source type"
    official_type = src.source_type in OFFICIAL_TYPES
    hj = judge_host(src.canonical_url, agency_name, state)
    if src.is_fixture:
        official_host = official_type  # fixtures declare their own type
    else:
        official_host = hj.is_official is True
    if not (official_type and official_host):
        return SourceQuality.UNVERIFIED, TemporalStatus.UNCERTAIN, f"not official: type={src.source_type} host={hj.basis}"
    eff = src.effective_date or src.publication_date
    if src.superseded_by:
        return SourceQuality.OFFICIAL_HISTORICAL, TemporalStatus.HISTORICAL, f"superseded by {src.superseded_by}"
    if eff is None:
        return SourceQuality.OFFICIAL_PARTIAL, TemporalStatus.UNCERTAIN, "official but undated"
    if (today - eff).days > CURRENT_WINDOW_YEARS * 365:
        return (
            SourceQuality.OFFICIAL_PARTIAL,
            TemporalStatus.UNCERTAIN,
            f"official, dated {eff}, older than {CURRENT_WINDOW_YEARS}y: currency unknown",
        )
    return SourceQuality.OFFICIAL_CURRENT, TemporalStatus.CURRENT, f"official, dated {eff}"


def classify_all(store: Store, today: date | None = None) -> StageRun:
    today = today or date.today()
    sources = store.sources()
    run = start_run(store, "source_classification", str(len(sources)))
    stats: Counter[str] = Counter()
    with store.tx():
        # supersession by date within (agency, source_type, title-ish) is decided in conflicts stage; here only quality
        for s in sources:
            a = store.get_agency(s.agency_or_jurisdiction or "")
            q, t, why = classify_source(s, a.canonical_name if a else "", a.state if a else None, today)
            if q != s.source_quality:
                store.update_source_status(s.source_id, field="source_quality", new_value=q, reason=why, run_id=run.run_id)
            if t != s.temporal_status:
                store.update_source_status(s.source_id, field="temporal_status", new_value=t, reason=why, run_id=run.run_id)
            stats[q] += 1
    return finish_run(store, run, dict(stats))
