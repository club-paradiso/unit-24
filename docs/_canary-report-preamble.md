# Canary report — narrative summary (hand-written; tables below are generated)

**Run date:** 2026-09-20. **Inputs:** `data/canary/canary_seed.jsonl` (100 agencies),
`data/canary/discovery_leads.jsonl` (recorded search results),
`data/raw/fbi_cde_frontend/agencies-by-state.json.gz` (FBI roster, 2018-06-28).

## Headline results

* **Agency discovered:** all 100 agencies have search evidence (two discovery rounds: the
  first stopped at 69 when the session search budget ran out; the second covered the rest).
  52 agencies also matched an FBI ORI exactly (54 confirmed record links), and a further
  1,183 FBI per-county reporting units were linked to canary state agencies as *proposed
  sub-units*.
* **Official domain discovered:** 78 / 100. The other 22 stay UNKNOWN by policy: their
  candidate hosts are agency-branded non-.gov domains (lasd.org, lvmpd.com, wmata.com,
  lawa.org, septa.org, myfwc.com, denvergov.org, dallaspolice.net, anchoragepolice.com,
  harriscountyso.org, honolulupd.org, mbta.com, mta.info, panynj.gov path, dfwairport.com,
  kalamazoopublicsafety.org), campus .edu hosts (police.utexas.edu, ucpd.berkeley.edu,
  dps.osu.edu, dpps.msu.edu), or a state portal whose result titles did not name the agency
  (in.gov for Indiana State Police, mass.gov for Massachusetts State Police). Maricopa County
  Sheriff's Office returned no agency-operated host at all.
* **Radio-policy source discovered (lead only):** 136 official-host leads whose title/URL
  carries radio-protocol terms, across 57 agencies (68 agencies have at least one official
  document candidate of any kind). Strongest examples: Florida Highway Patrol Policy 14.01
  Communications (flhsmv.gov), Indiana State Police "Communications Procedures" PDF
  (in.gov/isp), Idaho State Police Procedure 07.12 Patrol Radio Operations (isp.idaho.gov),
  CHP "Aural Brevity Card" and HPM 50.1 (chp.ca.gov), Phoenix PD "Radio Codes – Numerical
  Order" PDF (phoenix.gov), Detroit PD "Radio Codes" list and Directive 301.1 Radio
  Procedures (detroitmi.gov), Wisconsin State Patrol P&P 5-8 Mobile Radio Communications
  (wsp.wi.gov), Houston PD General Order 400-10 Unit and Radio Numbering (houstontx.gov),
  Honolulu PD Telecommunications policy (honolulupd.org), Philadelphia PD Directive 7.1
  Police Radio (phillypolice.com), LASD Manual of Policy and Procedures radio sections
  (pars.lasd.org), Orange County SD "Radio Codes" page (ocsheriff.gov), Georgia DPS Policy
  14.04 Communications, LA Airport Police Chapter XIII Communications (lawa.org).
* **Current official protocol source:** 0. Every acquisition attempt against a government or
  agency host was denied by the build environment's egress policy (232 leads
  `blocked_egress`). No document was
  fetched, so no real-agency fact, conflict, phonetic alphabet or procedure exists in the
  corpus. Those columns read "UNKNOWN (no document acquired)" for all 100 agencies, which is
  the correct value.
* **Training eligibility:** INSUFFICIENT_EVIDENCE for all 100 real agencies.

## Failure modes observed (quantified)

| failure mode | count | handling |
|---|---|---|
| search budget exhausted before agency searched (round 1) | 31 agencies | `research_status=blocked`, explicit not-performed markers; resolved by round 2, markers superseded |
| egress-denied document fetch | 232 leads | `acquisition_status=blocked_egress` with proxy reason; resumable |
| plain-http lead upgraded to https before fetch | 2 leads (directives.chicagopolice.org) | still egress-denied |
| official host but agency not named in title (state portals) | 2 agencies | website stays UNKNOWN |
| agency-branded non-.gov or .edu host | 19 agencies | website stays UNKNOWN; host judged "plausible, unproven" |
| no agency-operated host in any result (Maricopa County SO, Miami PD) | 2 agencies | website UNKNOWN; site: search skipped for MCSO with explicit marker |
| site: search ignored by search backend (Wikipedia/Scribd leakage) | most C searches | off-host results classified as unrelated/secondary; nothing inferred |
| search result belongs to a different agency with a similar name (Harford vs Harris County, Fulton County Police vs Sheriff, Maryland Transit vs MTA) | several leads | host judgement is per agency name + state; leads stay leads |
| fuzzy registry matches that are different entities (Indiana State Excise Police, Miami Beach PD, Berkeley PD) | 19 proposals nationwide, 0 auto-merged | stored as `proposed`, tested |
| enthusiast/crowdsourced radio-code leads | 386 leads | `enthusiast_lead`, never fetched, never evidence |

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
