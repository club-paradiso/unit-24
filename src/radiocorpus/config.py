"""Filesystem layout. Everything is relative to the repository root unless overridden."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _root() -> Path:
    env = os.environ.get("RADIOCORPUS_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return Path.cwd()


@dataclass(frozen=True)
class Paths:
    root: Path = field(default_factory=_root)

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def documents(self) -> Path:
        return self.raw / "documents"

    @property
    def intermediate(self) -> Path:
        return self.data / "intermediate"

    @property
    def normalized(self) -> Path:
        return self.data / "normalized"

    @property
    def fixtures(self) -> Path:
        return self.data / "fixtures"

    @property
    def canary(self) -> Path:
        return self.data / "canary"

    @property
    def manifests(self) -> Path:
        return self.data / "manifests"

    @property
    def db(self) -> Path:
        return Path(os.environ.get("RADIOCORPUS_DB", self.intermediate / "corpus.sqlite"))

    def ensure(self) -> None:
        for p in (self.raw, self.documents, self.intermediate, self.normalized, self.fixtures, self.canary, self.manifests):
            p.mkdir(parents=True, exist_ok=True)


PATHS = Paths()
