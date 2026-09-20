"""Export JSON Schema for every persisted model to schemas/. Run: uv run python scripts/export_schemas.py"""

from __future__ import annotations

import json
from pathlib import Path

from radiocorpus.models import (
    Agency,
    AgencyLink,
    Conflict,
    DocumentLead,
    DocumentRecord,
    EligibilityDecision,
    ProtocolFact,
    RegistryRecord,
    Source,
    StageRun,
    TrainingItem,
)

OUT = Path(__file__).resolve().parents[1] / "schemas"
MODELS = [
    RegistryRecord,
    Agency,
    AgencyLink,
    DocumentLead,
    Source,
    DocumentRecord,
    ProtocolFact,
    Conflict,
    EligibilityDecision,
    TrainingItem,
    StageRun,
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for m in MODELS:
        (OUT / f"{m.__name__}.schema.json").write_text(json.dumps(m.model_json_schema(), indent=2, sort_keys=True) + "\n")
    print("wrote", len(MODELS), "schemas to", OUT)


if __name__ == "__main__":
    main()
