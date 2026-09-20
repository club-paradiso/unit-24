from __future__ import annotations

from pathlib import Path

import pytest

from radiocorpus.conflicts.detect import detect_conflicts
from radiocorpus.eligibility.policy import assign_all
from radiocorpus.extraction.stage import extract_all
from radiocorpus.fixtures import load_fixtures
from radiocorpus.provenance.classify import classify_all
from radiocorpus.store import Store
from radiocorpus.validation.rules import validate_all

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
CANARY = ROOT / "data" / "canary"
FBI = ROOT / "data" / "raw" / "fbi_cde_frontend" / "agencies-by-state.json.gz"


def run_fixture_pipeline(store: Store, doc_dir: Path) -> None:
    load_fixtures(store, FIXTURES, doc_dir)
    extract_all(store)
    classify_all(store)
    validate_all(store)
    detect_conflicts(store)
    assign_all(store)


@pytest.fixture
def store() -> Store:
    return Store()


@pytest.fixture
def fixture_store(tmp_path: Path) -> Store:
    s = Store()
    run_fixture_pipeline(s, tmp_path / "docs")
    return s


def fixture_agency_id(fid: str) -> str:
    from radiocorpus import ids

    return ids.agency_id("FIXTURE", fid)
