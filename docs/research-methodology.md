# Research methodology

## 1. Research universe

The universe is "every identifiable U.S. state and local law-enforcement agency". No single
authoritative, current, downloadable list exists. The datasets evaluated are documented with
authority, dates, coverage, omissions, identifiers, licensing and incorporation plan in
`data/manifests/registry_sources.json`. Summary:

| dataset | authority | reference date | unit | reachable in build session |
|---|---|---|---|---|
| CSLLEA 2018 (ICPSR 38771) | BJS | June 2018; published Oct 2022 | agency (17,541) | no (egress-blocked) |
| LEAR 2016 (ICPSR 36697) | BJS | Dec 2016 | general-purpose agency (15,810) | no |
| LEAIC 2012 (ICPSR 35158) | BJS/NACJD | 2012 | ORI↔FIPS crosswalk | no |
| FBI CDE agencies API | FBI CJIS | live | UCR reporting entity (ORI) | no |
| FBI CDE frontend snapshot | FBI CDE (GitHub fbi-cde) | 2018-06-28 | UCR reporting entity (23,243) | **yes** (git) |
| State POST directories | 50 state commissions | live, varies | certified agency | no |

The historical "about 17,500 agencies" figure is the **June 2018** CSLLEA count (17,541).
It is never presented as current. The corpus stores counts only alongside their reference
date, and the only nationwide roster actually loaded is labelled `FBI_CDE_FRONTEND_2018`.

## 2. Registry construction

* Every external row is stored verbatim as a `RegistryRecord` under a dated registry code.
* Canonical `Agency` rows are created from curated seeds (research hypotheses) and from
  registry rows that match nothing.
* Links between agencies and registry rows are explicit `AgencyLink` objects with a rule
  name as basis and a status (`confirmed` / `proposed` / `ambiguous`). Rules R1–R6 are
  documented in `registry/resolve.py`. Only exact normalized-name + same-state matches are
  confirmed automatically. Sub-units ("Highway Patrol: Sonoma County") are linked as
  *proposed sub-units*, never merged. Fuzzy matches require core-token overlap (Jaccard ≥
  0.6) and are stored as proposals; multiple candidates are stored as ambiguous.
* Sharing a dispatch centre, county, or name prefix is never a merge reason (tested).

## 3. Discovery protocol (per agency)

Three searches, recorded verbatim (query, rank, title, URL, timestamp, engine):

* **A** `"<name>" <ST> official website`
* **B** `"<name>" radio codes OR "ten codes" OR "10-codes" OR "phonetic alphabet" OR "radio procedures" OR "communications manual"`
* **C** `site:<official host> radio OR "10-codes" OR "ten-code" OR phonetic OR "communications" manual OR policy` (only when A/B revealed an official host)

Workers that ran the searches were instructed to copy results verbatim, never to add
knowledge, and to record refused searches explicitly as `search_not_performed` with the
reason. The classifier then decides, in code, whether a host is official and whether a title
suggests a radio-protocol document (`discovery/classify.py`).

## 4. Acquisition, extraction, validation

Only official candidate leads are fetched; robots.txt is honoured; bytes are hashed and stored
content-addressed. Deterministic parsers extract code tables, phonetic alphabets and
prescriptive procedure sentences with page/element locators and ≤400-character excerpts.
A model extractor is available behind an interface but disabled by default. Deterministic
validation rejects malformed codes, generic meanings and excerpt-less facts (kept, marked
rejected).

## 5. Cross-checking, conflicts, eligibility

Facts are grouped by (agency, fact type, key). Different normalized values from different
sources produce a stored `Conflict` with a kind (official vs official, current vs obsolete,
agency vs dispatch, secondary vs official, undated manual...). Resolution is attempted only
with evidence: temporal (newer dated official wins; older marked historical), jurisdictional
(agency's own manual beats dispatch/parent docs), quality (official beats secondary). Same-date
disagreement and undated-vs-dated official documents stay `unresolved`. Nothing is deleted.
Eligibility states are assigned by `eligibility/policy.py` (see docs/schema.md).

## 6. What was and was not executed in the build session

Executed: registry ingestion (23,243 + 100), resolution, discovery for all 100 canary
agencies from recorded search results (two rounds), acquisition attempts for 232 official
candidate leads, the full extraction→eligibility path on 7 synthetic fixture documents,
tests, invariants, exports.

Not executed (environment): fetching any government/agency document (all such hosts were
denied by the organization egress policy, recorded per lead as `blocked_egress`);
downloading CSLLEA/LEAR/LEAIC. Reproduction commands for each blocked operation are in
`docs/nationwide-expansion-plan.md`.
