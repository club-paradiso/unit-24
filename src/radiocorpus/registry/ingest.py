"""Stage 1: registry ingestion. Idempotent: re-running with the same file inserts nothing new."""

from __future__ import annotations

import hashlib
from pathlib import Path

from radiocorpus.models import StageRun
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.registry.adapters import get_adapter
from radiocorpus.store import Store


def file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def ingest_registry(store: Store, adapter_name: str, path: Path) -> StageRun:
    adapter = get_adapter(adapter_name)
    fp = f"{adapter_name}:{file_fingerprint(path)}"
    run = start_run(store, "registry_ingest", fp)
    inserted = skipped = 0
    with store.tx():
        for rec in adapter.records(path):
            if store.upsert_registry_record(rec, run.run_id):
                inserted += 1
            else:
                skipped += 1
    return finish_run(
        store, run, {"registry": adapter.registry_code, "snapshot_date": adapter.snapshot_date, "inserted": inserted, "skipped_existing": skipped}
    )
