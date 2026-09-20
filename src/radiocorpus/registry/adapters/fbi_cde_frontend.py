"""FBI Crime Data Explorer frontend roster (GitHub fbi-cde/crime-data-frontend,
public/data/agencies-by-state.json.gz, commit ddbd3077, 2018-06-28).

Unit of record: UCR reporting entity keyed by ORI. Not a census of agencies."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from radiocorpus.models import RegistryRecord

TYPE_HINTS = {
    "City": "municipal_police",
    "County": "sheriff_or_county_police",
    "State Police": "state_police_reporting_unit",
    "Other State Agency": "other_state_agency",
    "University or College": "university_police",
    "Tribal": "tribal_police",
    "Federal": "federal",
    "Other": "other",
    "Unknown": "unknown",
}


class FbiCdeFrontendAdapter:
    registry_code = "FBI_CDE_FRONTEND_2018"
    snapshot_date = "2018-06-28"

    def records(self, path: Path) -> Iterator[RegistryRecord]:
        opener = gzip.open if str(path).endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8") as f:  # type: ignore[operator]
            data = json.load(f)
        snap = date.fromisoformat(self.snapshot_date)
        for state, entries in sorted(data.items()):
            for ori, v in sorted(entries.items()):
                yield RegistryRecord(
                    registry=self.registry_code,
                    external_id=ori,
                    name=v.get("agency_name"),
                    state=state,
                    agency_type_hint=TYPE_HINTS.get(v.get("agency_type_name"), "unknown"),
                    county=v.get("primary_county"),
                    payload={"ori": ori, "state": state, **v},
                    registry_snapshot_date=snap,
                )
