from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from radiocorpus.models import RegistryRecord


class RegistryAdapter(Protocol):
    registry_code: str
    snapshot_date: str  # ISO date the snapshot represents (documented, not inferred)

    def records(self, path: Path) -> Iterator[RegistryRecord]: ...


def get_adapter(name: str) -> RegistryAdapter:
    if name == "fbi_cde_frontend":
        from radiocorpus.registry.adapters.fbi_cde_frontend import FbiCdeFrontendAdapter

        return FbiCdeFrontendAdapter()
    if name == "curated":
        from radiocorpus.registry.adapters.curated import CuratedSeedAdapter

        return CuratedSeedAdapter()
    if name == "delimited":
        from radiocorpus.registry.adapters.delimited import DelimitedAdapter

        return DelimitedAdapter()
    raise KeyError(f"unknown registry adapter {name!r}")
