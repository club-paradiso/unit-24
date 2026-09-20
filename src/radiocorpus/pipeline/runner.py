"""Run bookkeeping shared by all stages."""

from __future__ import annotations

from typing import Any

from radiocorpus import ids
from radiocorpus.models import StageRun
from radiocorpus.models.common import utcnow
from radiocorpus.store import Store


def start_run(store: Store, stage: str, fingerprint: str) -> StageRun:
    run = StageRun(run_id=ids.run_id(stage, fingerprint + utcnow().isoformat()), stage=stage, input_fingerprint=fingerprint)
    store.save_run(run)
    store.commit()
    return run


def finish_run(store: Store, run: StageRun, stats: dict[str, Any], status: str = "completed", notes: str | None = None) -> StageRun:
    run2 = run.model_copy(update={"finished_at": utcnow(), "status": status, "stats": stats, "notes": notes})
    store.save_run(run2)
    store.commit()
    return run2
