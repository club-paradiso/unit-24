# Canary report — narrative summary (hand-written; tables below are generated)

**Run date:** 2026-09-20. **Inputs:** `data/canary/canary_seed.jsonl` (100 agencies),
`data/canary/discovery_leads.jsonl` (recorded search results),
`data/raw/fbi_cde_frontend/agencies-by-state.json.gz` (FBI roster, 2018-06-28).

## Headline results

* **Agency discovered:** 69 agencies have search evidence; 36 of those also matched an FBI
  ORI exactly (54 exact matches in total), and a further 1,183 FBI per-county reporting
  units were linked to canary state agencies as *proposed sub-units*. 31 agencies were not
  searched (session budget) and are `blocked`; 16 of these still have an exact FBI ORI
  match from the registry stage, so they are known to exist but are unresearched.
* **Official domain discovered:** 59 / 69 searched agencies. The other 10 stay UNKNOWN by
  policy: their candidate hosts are agency-branded non-.gov domains (lapdonline.org,
  lasd.org, lvmpd.com, wmata.com, lawa.org, septa.org, myfwc.com, denvergov.org,
  police.utexas.edu) or a state portal whose result titles did not name the agency
  (in.gov for Indiana State Police, mass.gov for Massachusetts State Police).
* **Radio-policy source discovered (lead only):** 85 official-host leads whose title/URL
  carries radio-protocol terms, across 34 agencies (40 agencies have at least one official document candidate of any kind). Strongest examples: Florida Highway
  Patrol Policy 14.01 Communications (flhsmv.gov), Indiana State Police "Communications
  Procedures" PDF (in.gov/isp), Idaho State Police Procedure 07.12 Patrol Radio Operations
  (isp.idaho.gov), CHP "Aural Brevity Card" and HPM 50.1 (chp.ca.gov), Philadelphia PD
  Directive 7.1 Police Radio (phillypolice.com), LASD Manual of Policy and Procedures radio
  sections (pars.lasd.org), Orange County SD "Radio Codes" page (ocsheriff.gov), Georgia DPS
  Policy 14.04 Communications, LA Airport Police Chapter XIII Communications (lawa.org).
* **Current official protocol source:** 0. Every acquisition attempt against a government or
  agency host was denied by the build environment's egress policy (137 leads
  `blocked_egress`, 2 `http_error` 403 on directives.chicagopolice.org). No document was
  fetched, so no real-agency fact, conflict, phonetic alphabet or procedure exists in the
  corpus. Those columns read "UNKNOWN (no document acquired)" for all 100 agencies, which is
  the correct value.
* **Training eligibility:** INSUFFICIENT_EVIDENCE for all 100 real agencies.

## Failure modes observed (quantified)

| failure mode | count | handling |
|---|---|---|
| search budget exhausted before agency searched | 31 agencies | `research_status=blocked`, explicit not-performed markers; re-run list in nationwide-expansion-plan.md |
| egress-denied document fetch | 137 leads | `acquisition_status=blocked_egress` with proxy reason; resumable |
| HTTP 403 from reachable host | 2 leads | recorded, not retried |
| official host but agency not named in title (state portals) | 2 agencies | website stays UNKNOWN |
| agency-branded non-.gov host | 8 agencies | website stays UNKNOWN; host judged "plausible, unproven" |
| search tool returned neighbouring agencies instead of target (Miami PD) | 1 agency | website UNKNOWN; leads kept as unrelated/secondary |
| fuzzy registry matches that are different entities (Indiana State Excise Police, Miami Beach PD, Berkeley PD) | 19 proposals nationwide, 0 auto-merged | stored as `proposed`, tested |
| enthusiast/crowdsourced radio-code leads | 256 leads | `enthusiast_lead`, never fetched, never evidence |

## Fixture corpus (synthetic, state ZZ) — proves the fact path end to end

7 documents, 89 candidate facts (all passed validation), 3 conflicts:
current-vs-obsolete official manuals resolved temporally (older fact marked historical,
kept); agency policy vs dispatch-centre SOP resolved jurisdictionally (dispatch value kept
as RESEARCH_ONLY); two equally dated official documents disagreeing on "Signal 7" left
unresolved (both facts CONFLICT_REQUIRES_REVIEW). A scanner fan page that contradicts the
official manual is UNVERIFIED/RESEARCH_ONLY. An undated sheriff policy yields
PLAYABLE_WITH_LIMITATIONS. A neighbouring township sharing the same dispatch centre has no
facts and is INSUFFICIENT_EVIDENCE. Fact eligibility: 41 PLAYABLE_VERIFIED, 43
PLAYABLE_WITH_LIMITATIONS, 1 HISTORICAL_ONLY, 2 RESEARCH_ONLY, 2 CONFLICT_REQUIRES_REVIEW.
All 8 invariants hold.
