from radiocorpus.models import RegistryRecord
from radiocorpus.models.common import LinkStatus
from radiocorpus.registry.ingest import ingest_registry
from radiocorpus.registry.resolve import Resolver
from radiocorpus.store import Store
from tests.conftest import CANARY, FBI


def _rec(registry, ext, name, state, hint=None):
    return RegistryRecord(registry=registry, external_id=ext, name=name, state=state, agency_type_hint=hint)


def _seeded(store: Store, seeds):
    for s in seeds:
        store.upsert_registry_record(_rec("CURATED_CANARY", *s))
    Resolver(store).seed_curated("CURATED_CANARY")


def test_exact_match_confirms_and_records_registry_id(store):
    _seeded(store, [("C1", "Moab Police Department", "UT", "municipal_police")])
    store.upsert_registry_record(_rec("FBI_X", "UT0100100", "Moab Police Department", "UT", "municipal_police"))
    rep = Resolver(store).resolve_registry("FBI_X")
    assert rep.confirmed_links == 1 and rep.created == 0
    a = next(iter(store.agencies()))
    assert a.source_registry_ids == {"CURATED_CANARY": ["C1"], "FBI_X": ["UT0100100"]}


def test_ingestion_is_idempotent_and_dedupes(store):
    _seeded(store, [("C1", "Moab Police Department", "UT")])
    for _ in range(3):
        store.upsert_registry_record(_rec("FBI_X", "UT0100100", "Moab Police Department", "UT"))
        Resolver(store).resolve_registry("FBI_X")
    assert store.agency_count() == 1
    assert len(store.links()) == 2  # seed link + one FBI link, not three


def test_false_positive_merge_prevented(store):
    """City PD vs campus PD in the same city, sub-string names, must never be CONFIRMED together."""
    _seeded(
        store,
        [
            ("C1", "University of California, Berkeley Police Department", "CA"),
            ("C2", "Miami Police Department", "FL"),
            ("C3", "Indiana State Police", "IN"),
        ],
    )
    store.upsert_registry_record(_rec("FBI_X", "CA0010300", "Berkeley Police Department", "CA"))
    store.upsert_registry_record(_rec("FBI_X", "FL0130700", "Miami Beach Police Department", "FL"))
    store.upsert_registry_record(_rec("FBI_X", "INIEP0000", "Indiana State Excise Police", "IN"))
    rep = Resolver(store).resolve_registry("FBI_X")
    assert rep.confirmed_links == 0
    assert store.agency_count() == 6  # three seeds + three own agencies
    for ext in ("CA0010300", "FL0130700"):
        links = store.links_for_record("FBI_X", ext)
        assert all(lk.status == LinkStatus.CONFIRMED and lk.agency_id != _seed_id(store, ext) for lk in links)
        assert not any(lk.status == LinkStatus.PROPOSED for lk in links)
    excise = [lk for lk in store.links_for_record("FBI_X", "INIEP0000") if lk.status != LinkStatus.CONFIRMED]
    assert all(lk.status == LinkStatus.PROPOSED for lk in excise)  # kept for review, never merged


def _seed_id(store, ext):
    return None


def test_same_state_same_name_is_ambiguous_not_merged(store):
    _seeded(store, [("C1", "Franklin Police Department", "OH"), ("C2", "Franklin Police Department", "OH")])
    store.upsert_registry_record(_rec("FBI_X", "OH1", "Franklin Police Department", "OH"))
    rep = Resolver(store).resolve_registry("FBI_X")
    assert rep.ambiguous_links == 1
    links = store.links_for_record("FBI_X", "OH1")
    assert {lk.status for lk in links} == {LinkStatus.AMBIGUOUS}
    assert all(lk.competing_agency_ids for lk in links)


def test_reporting_subunits_link_as_proposed_subunit(store):
    _seeded(store, [("C1", "California Highway Patrol", "CA")])
    store.upsert_registry_record(_rec("FBI_X", "CA0499900", "Highway Patrol: Sonoma County", "CA", "state_police_reporting_unit"))
    rep = Resolver(store).resolve_registry("FBI_X")
    assert rep.subunit_links == 1
    lk = store.links_for_record("FBI_X", "CA0499900")[0]
    assert lk.link_kind == "subunit" and lk.status == LinkStatus.PROPOSED
    a = store.get_agency(lk.agency_id)
    assert "FBI_X" not in a.source_registry_ids  # proposed sub-unit does not become an identity


def test_different_state_never_matches(store):
    _seeded(store, [("C1", "Springfield Police Department", "IL")])
    store.upsert_registry_record(_rec("FBI_X", "MO1", "Springfield Police Department", "MO"))
    rep = Resolver(store).resolve_registry("FBI_X")
    assert rep.confirmed_links == 0 and rep.created == 1


def test_shared_dispatch_or_county_is_not_a_merge_reason(store):
    _seeded(store, [("C1", "Alpha Police Department", "TX")])
    store.upsert_registry_record(_rec("FBI_X", "TX1", "Beta Police Department", "TX"))
    a = next(iter(store.agencies()))
    store.upsert_agency(a.model_copy(update={"county": "Travis", "dispatch_provider": "Travis Regional Dispatch"}))
    rep = Resolver(store).resolve_registry("FBI_X")
    assert rep.confirmed_links == 0 and store.agency_count() == 2


def test_real_canary_against_fbi_snapshot(tmp_path):
    s = Store()
    ingest_registry(s, "curated", CANARY / "canary_seed.jsonl")
    ingest_registry(s, "fbi_cde_frontend", FBI)
    r = Resolver(s)
    r.seed_curated("CURATED_CANARY")
    rep = r.resolve_registry("FBI_CDE_FRONTEND_2018")
    assert store_counts(s) == (100 + rep.created, 23243)
    assert rep.confirmed_links >= 50 and rep.ambiguous_links == 0
    # a UC Berkeley trap must not have merged the city PD
    ucb = s.find_agencies_by_name("CA", "University of California, Berkeley")[0]
    assert "CA0010300" not in ucb.source_registry_ids.get("FBI_CDE_FRONTEND_2018", [])


def store_counts(s: Store):
    return s.agency_count(), s.registry_count("FBI_CDE_FRONTEND_2018")


def test_second_run_changes_nothing(tmp_path):
    s = Store()
    ingest_registry(s, "curated", CANARY / "canary_seed.jsonl")
    ingest_registry(s, "fbi_cde_frontend", FBI)
    r = Resolver(s)
    r.seed_curated("CURATED_CANARY")
    r.resolve_registry("FBI_CDE_FRONTEND_2018")
    before = (s.agency_count(), len(s.links()))
    run2 = ingest_registry(s, "fbi_cde_frontend", FBI)
    assert run2.stats["inserted"] == 0 and run2.stats["skipped_existing"] == 23243
    r.resolve_registry("FBI_CDE_FRONTEND_2018")
    assert (s.agency_count(), len(s.links())) == before
