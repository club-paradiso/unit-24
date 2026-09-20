"""Generic delimited adapter for BJS/ICPSR-style files (CSLLEA 2018 = ICPSR 38771,
LEAR 2016 = ICPSR 36697, LEAIC 2012 = ICPSR 35158).

Those files could not be downloaded in the build session (ICPSR and bjs.ojp.gov are
egress-blocked), so the column map is supplied at run time via a JSON sidecar rather than
hard-coded from memory. Required keys: registry_code, snapshot_date, id_column, name_column,
state_column; optional: type_column, county_column, delimiter, encoding."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from radiocorpus.models import RegistryRecord


class DelimitedAdapter:
    registry_code = "DELIMITED"
    snapshot_date = "unknown"

    def records(self, path: Path) -> Iterator[RegistryRecord]:
        spec_path = path.with_suffix(path.suffix + ".map.json")
        if not spec_path.exists():
            raise FileNotFoundError(f"column map sidecar required: {spec_path}")
        spec = json.loads(spec_path.read_text())
        self.registry_code = spec["registry_code"]
        self.snapshot_date = spec["snapshot_date"]
        snap = date.fromisoformat(self.snapshot_date)
        with path.open(encoding=spec.get("encoding", "utf-8"), newline="") as f:
            reader = csv.DictReader(f, delimiter=spec.get("delimiter", ","))
            for row in reader:
                ext = row[spec["id_column"]].strip()
                if not ext:
                    continue
                yield RegistryRecord(
                    registry=self.registry_code,
                    external_id=ext,
                    name=(row.get(spec["name_column"]) or "").strip() or None,
                    state=(row.get(spec["state_column"]) or "").strip().upper() or None,
                    agency_type_hint=(row.get(spec.get("type_column", "")) or "").strip() or None,
                    county=(row.get(spec.get("county_column", "")) or "").strip() or None,
                    payload=dict(row),
                    registry_snapshot_date=snap,
                )
