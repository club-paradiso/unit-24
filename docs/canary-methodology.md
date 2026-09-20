# Canary methodology

## Purpose

Before trusting the pipeline on ~20,000 agencies, exercise it on 100 deliberately
heterogeneous agencies and measure what it finds, what it cannot find, and where it fails.

## Selection (data/canary/canary_seed.jsonl)

| bucket | n | rule |
|---|---|---|
| state_principal | 50 | the principal state police / highway patrol organisation in each state. Where the patrol is a division of a DPS (AZ, FL, GA, IA, MN, MS, OK, SC, TX, AL/ALEA) the seed names the division the public knows, with the parent noted. Hawaii has no state police; the seed is the Department of Law Enforcement (2024), flagged for confirmation. Nevada's renamed State Police is flagged for confirmation. |
| municipal | 20 | 17 large/medium departments across regions (incl. consolidated LVMPD, Honolulu city-county) + 3 small towns with likely thin documentation (Moab UT, Bar Harbor ME, Ketchum ID) |
| sheriff | 10 | 7 large, 1 medium, 2 tiny (Loving County TX, Hinsdale County CO) |
| special_jurisdiction | 20 | 5 transit, 4 university, 2 airport, 1 port authority, 2 park/conservation, 2 tribal, 2 consolidated public-safety, 1 capitol police, 1 school-district police |

Seed names are hypotheses. The canonical name is not corrected from search results
automatically; renames observed by workers (e.g. "Bar Harbor & Mount Desert Police
Department", "Nevada State Police Highway Patrol", "Hawaii Department of Law Enforcement")
are recorded in worker notes and lead titles for review.

## Execution

1. `ingest-registry curated` + `ingest-registry fbi_cde_frontend`, then `resolve`.
2. Discovery: 8 parallel search workers, 3 searches per agency (see
   research-methodology.md §3), results recorded verbatim to
   `data/canary/discovery_leads.jsonl` (1,938 lines: 1,786 results, 100 worker judgments,
   52 explicit not-performed markers).
3. `discover` classifies leads and sets official websites only on evidence.
4. `acquire` attempts every official candidate lead (139).
5. Fixtures loaded to exercise extraction → eligibility.
6. `extract`, `classify-sources`, `validate`, `crosscheck`, `assign`, `export`, `stats`,
   `check-invariants`, `canary-report`.

`uv run radiocorpus run-canary` reproduces steps 1 and 3–6 from the committed inputs.

## Known limitations of this run

* The session's web-search budget (200 calls) was exhausted after 69 agencies; 31 agencies
  have no search data and are marked `blocked`, not `no_public_source`.
* The search tool returned titles and URLs only (no snippets), so lead classification relies
  on title/URL terms.
* All government and agency hosts were egress-denied from the build container, so no real
  document was acquired and no real protocol fact exists in the corpus. Fact-level results in
  the report come from the synthetic fixture corpus only.
