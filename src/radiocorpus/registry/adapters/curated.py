"""Curated seed rows (e.g. the canary set). Each row is a research hypothesis: the agency is
believed to exist under this name. Existence is confirmed only by discovery evidence."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from radiocorpus.models import RegistryRecord


class CuratedSeedAdapter:
    registry_code = "CURATED_CANARY"
    snapshot_date = "2026-09-20"

    def records(self, path: Path) -> Iterator[RegistryRecord]:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                yield RegistryRecord(
                    registry=self.registry_code,
                    external_id=row["canary_id"],
                    name=row["seed_name"],
                    state=row["state"],
                    agency_type_hint=row.get("agency_type"),
                    payload=row,
                )
