import json

from radiocorpus.registry.adapters import get_adapter
from tests.conftest import CANARY, FBI


def test_fbi_adapter_reads_snapshot():
    recs = list(get_adapter("fbi_cde_frontend").records(FBI))
    assert len(recs) == 23243
    assert all(r.registry == "FBI_CDE_FRONTEND_2018" and r.registry_snapshot_date.isoformat() == "2018-06-28" for r in recs[:50])
    assert all(len(r.external_id) == 9 for r in recs)


def test_curated_adapter_reads_canary():
    recs = list(get_adapter("curated").records(CANARY / "canary_seed.jsonl"))
    assert len(recs) == 100 and len({r.external_id for r in recs}) == 100
    assert sum(1 for r in recs if r.payload["selection_bucket"] == "state_principal") == 50


def test_delimited_adapter_requires_sidecar(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("ID,NAME,ST\n1,Alpha PD,TX\n2,,TX\n")
    try:
        list(get_adapter("delimited").records(p))
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass
    (tmp_path / "x.csv.map.json").write_text(
        json.dumps({"registry_code": "TEST_2020", "snapshot_date": "2020-01-01", "id_column": "ID", "name_column": "NAME", "state_column": "ST"})
    )
    recs = list(get_adapter("delimited").records(p))
    assert [r.name for r in recs] == ["Alpha PD", None]
    assert recs[0].registry == "TEST_2020"
