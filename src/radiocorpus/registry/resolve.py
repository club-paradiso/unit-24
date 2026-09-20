"""Entity resolution between canonical agencies and registry records.

Rules (in order):
  R1  A registry record that already has a CONFIRMED identity link is left alone.
  R2  Curated seed rows create/own a canonical agency (agency_id derives from the seed id).
  R3  A registry record matches a curated agency as IDENTITY only when the normalized names
      are equal AND the states are equal (deterministic exact match). Score 1.0, CONFIRMED.
  R4  If the record is a UCR reporting sub-unit ("Agency: Qualifier") whose head normalizes
      to the agency's name in the same state, it is linked as SUBUNIT (PROPOSED, never
      merged into a different agency).
  R4b Same as R4 but with the state name prepended to the head (rosters often omit it).
  R5  Fuzzy candidates (core-token Jaccard >= CORE_JACCARD_MIN and token-sort similarity >= FUZZY_MIN, same state) are stored
      as PROPOSED when exactly one candidate exists, or AMBIGUOUS when several exist. No
      canonical row is merged or renamed on a fuzzy match.
  R6  Registry records that match nothing get their own canonical agency with
      research_status=REGISTRY_ONLY. Sharing a dispatch centre, county, or name prefix
      with another agency is never grounds for merging.

Nothing here infers protocol facts; this is identity only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz

from radiocorpus import ids
from radiocorpus.models import Agency, AgencyLink, RegistryRecord
from radiocorpus.models.common import AgencyType, LinkStatus, ResearchStatus
from radiocorpus.normalization.names import core_tokens, normalize_name, split_reporting_unit
from radiocorpus.normalization.states import STATE_NAMES
from radiocorpus.store import Store

FUZZY_MIN = 80.0
CORE_JACCARD_MIN = 0.6  # share most identifying tokens, not just one

_HINT_TO_TYPE = {
    "municipal_police": AgencyType.MUNICIPAL_POLICE,
    "sheriff_or_county_police": AgencyType.UNKNOWN,  # sheriff vs county police cannot be inferred from the hint alone
    "state_police_reporting_unit": AgencyType.TASK_FORCE_OR_REPORTING_UNIT,
    "other_state_agency": AgencyType.UNKNOWN,
    "university_police": AgencyType.UNIVERSITY_POLICE,
    "tribal_police": AgencyType.TRIBAL_POLICE,
    "federal": AgencyType.FEDERAL,
    "other": AgencyType.UNKNOWN,
    "unknown": AgencyType.UNKNOWN,
}


def agency_type_from_hint(hint: str | None, name: str | None) -> AgencyType:
    """Only deterministic, name-evident classifications. Otherwise UNKNOWN."""
    if hint in AgencyType.__members__.values():
        return AgencyType(hint)
    t = _HINT_TO_TYPE.get(hint or "", AgencyType.UNKNOWN)
    n = (name or "").lower()
    if hint == "sheriff_or_county_police":
        if "sheriff" in n:
            return AgencyType.SHERIFF
        if "police" in n:
            return AgencyType.COUNTY_POLICE
        return AgencyType.UNKNOWN
    if hint == "state_police_reporting_unit" and ":" not in (name or ""):
        return AgencyType.UNKNOWN  # a state-level row without county qualifier; keep unknown
    return t


@dataclass
class ResolutionReport:
    created: int = 0
    confirmed_links: int = 0
    subunit_links: int = 0
    proposed_links: int = 0
    ambiguous_links: int = 0
    skipped_existing: int = 0
    examples: list[str] = field(default_factory=list)


def agency_from_seed(rec: RegistryRecord) -> Agency:
    aid = ids.agency_id(rec.registry, rec.external_id)
    hint = rec.agency_type_hint
    atype = AgencyType(hint) if hint in AgencyType.__members__.values() else AgencyType.UNKNOWN
    return Agency(
        agency_id=aid,
        canonical_name=rec.name or rec.external_id,
        agency_type=atype,
        state=rec.state,
        source_registry_ids={rec.registry: [rec.external_id]},
        research_status=ResearchStatus.SEED_UNCONFIRMED,
        jurisdiction_description=rec.payload.get("notes") or None,
        notes=f"selection_bucket={rec.payload.get('selection_bucket')}" if rec.payload.get("selection_bucket") else None,
    )


def agency_from_registry_record(rec: RegistryRecord) -> Agency:
    aid = ids.agency_id(rec.registry, rec.external_id)
    head, qualifier = split_reporting_unit(rec.name or "")
    return Agency(
        agency_id=aid,
        canonical_name=rec.name or rec.external_id,
        agency_type=agency_type_from_hint(rec.agency_type_hint, rec.name),
        state=rec.state if rec.state else None,
        county=rec.county,
        source_registry_ids={rec.registry: [rec.external_id]},
        research_status=ResearchStatus.REGISTRY_ONLY,
        jurisdiction_description=f"UCR reporting unit qualifier: {qualifier}" if qualifier else None,
    )


class Resolver:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._index: dict[tuple[str | None, str], list[Agency]] = {}
        self._by_state: dict[str | None, list[Agency]] = {}

    def _build_index(self, agencies: list[Agency]) -> None:
        self._index.clear()
        self._by_state.clear()
        for a in agencies:
            self._index.setdefault((a.state, normalize_name(a.canonical_name)), []).append(a)
            for alt in a.alternate_names:
                self._index.setdefault((a.state, normalize_name(alt)), []).append(a)
            self._by_state.setdefault(a.state, []).append(a)

    def seed_curated(self, registry: str) -> ResolutionReport:
        rep = ResolutionReport()
        for rec in self.store.registry_records(registry):
            aid = ids.agency_id(rec.registry, rec.external_id)
            if self.store.get_agency(aid):
                rep.skipped_existing += 1
                continue
            self.store.upsert_agency(agency_from_seed(rec))
            self.store.upsert_link(
                AgencyLink(
                    link_id=ids.link_id(aid, rec.registry, rec.external_id),
                    agency_id=aid,
                    registry=rec.registry,
                    external_id=rec.external_id,
                    link_kind="identity",
                    status=LinkStatus.CONFIRMED,
                    basis="R2 curated seed owns its canonical agency",
                    score=1.0,
                )
            )
            rep.created += 1
        return rep

    def resolve_registry(self, registry: str, *, target_registry: str = "CURATED_CANARY", create_unmatched: bool = True) -> ResolutionReport:
        """Link records of `registry` to existing canonical agencies (those seeded from
        `target_registry`), preserving ambiguity. Unmatched records become REGISTRY_ONLY agencies."""
        rep = ResolutionReport()
        targets = [a for a in self.store.agencies() if target_registry in a.source_registry_ids]
        self._build_index(targets)
        for rec in self.store.registry_records(registry):
            existing = self.store.links_for_record(rec.registry, rec.external_id)
            if any(link.status == LinkStatus.CONFIRMED for link in existing):
                rep.skipped_existing += 1
                continue
            outcome = self._match_one(rec, rep)
            if outcome is None and create_unmatched:
                a = agency_from_registry_record(rec)
                if self.store.get_agency(a.agency_id) is None:
                    self.store.upsert_agency(a)
                    rep.created += 1
                self.store.upsert_link(
                    AgencyLink(
                        link_id=ids.link_id(a.agency_id, rec.registry, rec.external_id),
                        agency_id=a.agency_id,
                        registry=rec.registry,
                        external_id=rec.external_id,
                        link_kind="identity",
                        status=LinkStatus.CONFIRMED,
                        basis="R6 registry record is its own canonical agency",
                        score=1.0,
                    )
                )
        return rep

    def _match_one(self, rec: RegistryRecord, rep: ResolutionReport) -> str | None:
        name = rec.name or ""
        norm = normalize_name(name)
        exact = self._index.get((rec.state, norm), [])
        if len(exact) == 1:
            a = exact[0]
            self._attach(a, rec, "identity", LinkStatus.CONFIRMED, "R3 exact normalized name + state", 1.0)
            rep.confirmed_links += 1
            return a.agency_id
        if len(exact) > 1:
            self._ambiguous(rec, exact, "R3 exact name matches multiple canonical agencies", rep)
            return exact[0].agency_id
        head, qualifier = split_reporting_unit(name)
        if qualifier:
            hn = normalize_name(head)
            heads = self._index.get((rec.state, hn), [])
            if not heads and rec.state in STATE_NAMES:
                # R4b: rosters often drop the state name ("Highway Patrol: Sonoma County" in CA)
                heads = self._index.get((rec.state, normalize_name(f"{STATE_NAMES[rec.state]} {head}")), [])
            if len(heads) == 1:
                self._attach(heads[0], rec, "subunit", LinkStatus.PROPOSED, f"R4 reporting sub-unit of '{head}' ({qualifier})", 0.95)
                rep.subunit_links += 1
                return heads[0].agency_id
            if len(heads) > 1:
                self._ambiguous(rec, heads, "R4 sub-unit head matches multiple agencies", rep)
                return heads[0].agency_id
        # R5 fuzzy within state, core tokens must overlap
        cands: list[tuple[float, Agency]] = []
        rec_core = core_tokens(head)
        for a in self._by_state.get(rec.state, []):
            a_core = core_tokens(a.canonical_name)
            if not rec_core or not a_core:
                continue
            jaccard = len(rec_core & a_core) / len(rec_core | a_core)
            if jaccard < CORE_JACCARD_MIN:
                continue  # "Miami Beach PD" vs "Miami PD", "Berkeley PD" vs "UC Berkeley PD": different entities
            score = fuzz.token_sort_ratio(normalize_name(head), normalize_name(a.canonical_name))
            if score >= FUZZY_MIN:
                cands.append((score, a))
        if len(cands) == 1:
            score, a = cands[0]
            self._attach(a, rec, "identity", LinkStatus.PROPOSED, f"R5 fuzzy token-set match score={score:.1f}; requires review", score / 100)
            rep.proposed_links += 1
            if len(rep.examples) < 20:
                rep.examples.append(f"PROPOSED {rec.external_id} '{name}' -> '{a.canonical_name}' ({score:.0f})")
            return None  # proposed links do not prevent the record from being its own agency
        if len(cands) > 1:
            self._ambiguous(rec, [a for _, a in cands], "R5 several fuzzy candidates", rep)
            return None
        return None

    def _attach(self, a: Agency, rec: RegistryRecord, kind: str, status: LinkStatus, basis: str, score: float) -> None:
        self.store.upsert_link(
            AgencyLink(
                link_id=ids.link_id(a.agency_id, rec.registry, rec.external_id),
                agency_id=a.agency_id,
                registry=rec.registry,
                external_id=rec.external_id,
                link_kind=kind,
                status=status,
                basis=basis,
                score=score,
            )
        )
        if status == LinkStatus.CONFIRMED and kind == "identity":
            idsmap = dict(a.source_registry_ids)
            lst = list(idsmap.get(rec.registry, []))
            if rec.external_id not in lst:
                lst.append(rec.external_id)
            idsmap[rec.registry] = lst
            a2 = a.model_copy(update={"source_registry_ids": idsmap})
            if rec.county and not a.county and ":" not in (rec.name or ""):
                a2 = a2.model_copy(update={"county": rec.county})
            self.store.upsert_agency(a2)

    def _ambiguous(self, rec: RegistryRecord, cands: list[Agency], basis: str, rep: ResolutionReport) -> None:
        others = [a.agency_id for a in cands]
        for a in cands:
            self.store.upsert_link(
                AgencyLink(
                    link_id=ids.link_id(a.agency_id, rec.registry, rec.external_id),
                    agency_id=a.agency_id,
                    registry=rec.registry,
                    external_id=rec.external_id,
                    link_kind="identity",
                    status=LinkStatus.AMBIGUOUS,
                    basis=basis,
                    competing_agency_ids=[o for o in others if o != a.agency_id],
                )
            )
        rep.ambiguous_links += 1
