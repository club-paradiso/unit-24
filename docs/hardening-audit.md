# Independent real-source validation and hardening audit

Engineering status: **NOT_READY**. Nationwide discovery and extraction must not begin.
The code now fails closed on the reproduced evidence-policy defects, but real extraction
quality and validation coverage do not meet the requested readiness gate.

## 1. Baseline repository state

Audited PR #1, “Foundation sprint: US Public Safety Radio Protocol Corpus data layer,”
head `48238acab2349418b1d0f88e3fc580ef7a84042b`, branch
`claude/radio-protocol-corpus-foundation-mm5s9g`, based on main
`ece5d7c9a403806ae226f42d873a5701ea277b97`. No merge was performed.
The baseline had 61 passing tests, a clean ruff check, no Actions workflow and zero
acquired real agency documents. Its fixture corpus was evidence of synthetic behavior,
not validated real extraction. The 2018 FBI registry contained 23,243 reporting units.

Direct git transport was unavailable; exact repository files were materialized through
the GitHub connector. Remote audit commits are built on the actual PR head, not the
local materialization history. The first audit commit added CI and failing regressions
before the identity fix: six failed and three passed.

## 2. Confirmed defects

Miami Police Department, FL (`agy_d85989588c1a440c`, ORI FL0130600), actually stored
`https://www.southmiamifl.gov/184/Police-Department`. Its note identified search A rank 1
and the South Miami Police Department title. This was reproduced from normalized data,
not inferred from the PR description. The original assertion is retained in
[data/audit/website_quarantine.jsonl](../data/audit/website_quarantine.jsonl).

`judge_host` accepted government suffixes, `title_mentions_agency` accepted 60% overlap
of core name tokens, and discovery selected the first qualifying result. Miami's one
core token matched South Miami. A fallback could retain the contaminated old website.
These rules are replaced by explicit reviewed target/name/state/host evidence; search
ranking and government hosting never automatically assign a website. All 59 legacy
search-only website assertions are quarantined, not asserted to be 59 wrong entities.

Other confirmed unsafe assumptions were the ten-year currentness rule, source-ID-only
corroboration, parent/dispatcher applicability inheritance, deterministic auto-verification,
and conflict preference inferred from dates or document type.

## 3. Additional defects

[The severity ledger](../data/audit/findings.json) records every finding and disposition.
Additional defects included skipped HTML paragraphs, hash-deduplication suppressing
source-specific extraction, malformed PDF batch failure, error HTML recorded as a
successful acquisition, stale human reports, missing evidence in exports and vacuous CI
invariants against an empty database.

Sol independently reproduced unsafe paths involving fabricated acquisition metadata,
missing/stale conflicts, verified snapshot rows without review/eligibility, missing
human-review provenance, issuer/host confusion, uncertain facts, non-expiring currentness
observations and unbound conflict-resolution labels. These paths have regression gates.
Structured conflict resolution is deliberately unavailable; disagreement remains unresolved.

Open BLOCKERs are real parser precision and incomplete validation coverage. HIGH gaps
include real temporal-pair validation and registry currency. Scanned extraction is gated.

## 4. Source documents actually retrieved

The [generated source ledger](real-source-metrics.md) links every attempted URL and
reports retrieval outcome, PDF pages, native-text coverage and candidate counts. Original
hashes, response metadata and reproducible URLs are in `data/audit/retrieval/`.

Six PDFs were actually saved and processed: CHP aural brevity card (2 pages), Indiana
Communications Procedures (9), Chicago pursuit directive G03-03-01 (11), Philadelphia
Directive 7.1 (31), Boston Rule 322 property policy (4), and WSP-hosted FBI NCIC Code
Manual (1,231). The latter two illustrate poor topic selection; NCIC is not WSP radio
protocol. Six usable HTML responses and two unusable HTML responses were also saved.
The Denver error page and LASD empty response are explicitly excluded from usable
capture counts. Their original retrieval labels are preserved for audit.

Idaho's 18-page Patrol Radio Operations document was inspected through the public web
reader, including its opening procedure pages, but original-byte acquisition returned
502. It is not counted as an acquired PDF or included in the deterministic extraction
statistics. BART's public page was inspected separately through the reader; direct
acquisition returned 403. Cloud Browser inspection did not resolve the failed original
acquisitions. No authentication, CAPTCHA or access-control bypass was attempted.

## 5. Agencies actually validated

The sample targeted 20 agencies: seven state, seven major municipal, four county/sheriff,
and two transit agencies. All named mandatory agencies were attempted. Twenty targets
is not twenty validated protocols. Four agencies had complete candidate sets checked
against their source text: CHP, Indiana State Police, Chicago PD and Philadelphia PD.
The CHP card's two rendered pages were also visually inspected.

No agency's current radio protocol was established sufficiently for learner playback.
FHP, NYPD, LAPD, Seattle, Idaho and BART original-byte attempts failed. County and special
jurisdiction acquisitions did not yield a validated protocol fact set. These are unresolved
coverage gaps, not “no public policy exists” findings.

## 6. Real extraction statistics

The pipeline processed 14 saved responses and produced 338 candidates: 56 code meanings,
229 phonetic mappings, 51 procedure rules and 2 alphabet-system assertions. Six PDFs
contained 1,288 pages. The 1,231-page NCIC manual dominates this count and contributes
214 candidates; these totals must not be presented as radio-protocol coverage.

After conflict detection, 244 candidates require conflict review and 94 are research-only.
All 338 are unverified; none is playable. Source classification remains UNVERIFIED because
reviewed identity/issuer/currentness evidence was not completed in the corpus. Minimal
fact excerpts, source IDs, hashes, physical page locators, rule/version and extraction
method are retained in the audit exports.

Failure patterns: adjacent PDF columns merged or truncated code meanings; section labels
and prose were parsed as phonetic mappings; a near-match alphabet was labeled APCO despite
local differences; a Philadelphia revision date was treated as an 11-code; generic words
such as “copy” yielded spurious radio acknowledgement rules. Native text extraction success
therefore does not imply correct facts. No statistical recall is claimed.

## 7. 116-fact source-comparison audit

[Machine-readable results](../data/audit/fact_audit.jsonl) cover CHP 85, Indiana 8,
Chicago 8 and Philadelphia 15 candidates. Every row records exact support, attribution,
locator, authority, currentness, applicability and expected-answer safety. Reviewer identity
is GPT-6 Astra; `human_review` is false. These observations never set HUMAN_ACCEPTED.

61/116 meanings were supported (52.6%). Only 24/116 complete facts, including normalized
metadata and scope, were supported (20.7%). All 116 physical-page locators were traceable,
but a correct page does not validate an interpretation. Zero candidates were learner-safe
because currentness was not established. These are purposive audit proportions, not an
estimate of national parser precision. Ground truth was not fully enumerated, so recall
is unknown. Signal/status, ordered structures, interoperability and callsign/unit-convention
strata are missing; the requested full stratification remains incomplete.

## 8. OCR and format results

Native PDF, multi-column PDF/card, PDF tabular content, revision histories, HTML pages,
non-.gov official material and cross-government hosting were encountered. HTML table
extraction is demonstrated by synthetic regression; a real protocol HTML table was not
validated. No real image-only scanned PDF was acquired. No OCR engine success is claimed.

Pages with fewer than 20 native text characters and embedded images raise OCRRequired
unless an explicit backend is provided. A synthetic image PDF and mock backend test the
fallback contract, page locators and method marker. Native text does not invoke OCR.
Malformed PDFs are isolated. Mixed scan/text pages and real OCR accuracy remain unvalidated.

## 9. Temporal/currentness findings

CHP's URL date and card revision differ; the filename cannot establish revision status.
Indiana's 2015 policy names a 2012 predecessor, but that predecessor was not acquired.
Philadelphia contains multiple revision dates; Chicago includes a generated “current as
of” footer. These observations do not prove current operative agency radio rules.
No real old/new policy pair was acquired and validated. Temporal conflict tests remain
synthetic. Historical evidence is preserved; an age window never proves currentness.

Typed currentness evidence distinguishes confirmed, presumed, undated, historical,
superseded and unknown. Current observations require an explicit recheck deadline.
Expired observations become presumed; future and superseded evidence cannot play.

## 10. Entity-resolution findings

Regressions cover Miami/South Miami/Miami Beach/county entities, neighboring city names,
Berkeley/UC Berkeley, Portland ME/OR, WSP/DC MPD and Orange County CA/FL. Search titles are
only candidate filters. Actual acceptance requires reviewed identity evidence.

The legacy corpus also contained non-target discovery leads (for example court or
unrelated training/building-code material). The audit does not claim every quarantined
website was wrong. A governmental host proves neither target identity nor issuing authority.
WSP-hosted NCIC content is the real adversarial example for the new issuer gate.

## 11. Evidence and applicability findings

Distinct URLs, hashes, issuers and documented disjoint lineages are all required to count
independent corroboration. Repetition never grants playback. Shared dispatcher, parent,
county or state relationships do not grant applicability. Explicit reviewed evidence must
name targets, exact fact keys/types and effective periods. A same-entity shortcut additionally
requires reviewed issuing-authority proof; hosted third-party sources do not inherit it.

Playback requires actual matching bytes, confirmed currentness, applicable scope, explicitly
current fact status, structured human acceptance bound to the exact source/hash/value, and
no disagreement. No deterministic parser is eligible for auto-verification. Accepted facts
with missing local evidence fail closed; this is intentional for research exports.

## 12. Code changes and registry currency

Changes span models/schemas, discovery, acquisition, text extraction, classification,
conflicts, eligibility, invariants, export, reports, migration and CI. Shared-byte extraction
is source-specific; malformed documents fail individually; HTML leaf text is retained;
exports include transitive evidence sources, source owners and document manifests.

[Registry lineage design](registry-lineage.md) preserves the 2018 snapshot and permits
independent dated registries. Changed rows in the same snapshot now raise. Current BJS,
California POST, Miami-Dade and DCC pages were inspected. Observed identity/contract/name
changes are stored as proposals with unknown legal transition dates. Post-2018 formation,
merger and dissolution coverage remains incomplete; no current nationwide replacement
was claimed or loaded.

## 13. Tests added and changed

Identity regression was written before the fix. Added adversarial cases cover evidence
independence, explicit applicability, stale/recent/superseded/undated evidence, synthetic
OCR and malformed PDFs, HTML tables/paragraphs, per-source mirror extraction, HTTP-200
error pages, report consistency, registry snapshot collisions, acquired-byte integrity,
review provenance, issuer mismatch, uncertain facts, expiry and verified snapshot bypass.

Old tests that encoded automatic verification, date-based preference or secondary
playability were changed explicitly. The baseline 61-test green run is retained as a
baseline, not proof that those assumptions were safe.

## 14. Test and CI status

Python 3.12 CI runs `uv sync`, `uv run pytest`, `uv run ruff check src tests scripts`,
and `uv run radiocorpus check-invariants` on pull requests and pushes to main. The invariant
command checks committed snapshots and generated reports as well as the database.
Final local run: 109 tests passed; ruff and all invariant/report checks passed.
Local/remote results are recorded in `data/audit/verification.json` after publication.
A workflow file is not by itself evidence that GitHub Actions completed successfully.

## 15. Branch and PR

Audit branch: `astra/real-source-validation-hardening`. The separate draft PR targets
`claude/radio-protocol-corpus-foundation-mm5s9g`, not main. Neither PR is merged.
Publication details and commits are recorded in `data/audit/verification.json`.

## 16. Unresolved risks

Parser precision is unacceptable. Required fact families and agency strata lack adequate
real validation. Real OCR, operative temporal pairs, current registry coverage and source
review completeness remain gaps. Content-type success can still hide unsuitable material;
redirect chains and general document suitability need stronger acquisition provenance.
Currentness evidence is trusted reviewer testimony, not a cryptographic proof of government
status. No engineering schema can replace a truthful independent review.

Full third-party documents remain ignored local acquisitions. Git contains source URLs,
hashes, metadata, necessary short fact excerpts and authored synthetic fixtures. A new
checkout must retrieve the recorded bytes lawfully and verify the hashes to reproduce
real extraction; mutable/removed URLs may prevent exact reproduction.

## 17. Nationwide readiness decision

The engineering status at the beginning of this report is the sole readiness decision.
Evidence gates are materially stronger, but unresolved BLOCKERs prohibit nationwide work.
Zero eligible facts is a correct outcome when currentness and applicability are unproven.

## 18. Exact immediate next action

Review the stacked hardening PR, then run a bounded layout-aware extraction repair against
the saved CHP/Indiana/Chicago/Philadelphia documents, with an independently adjudicated
correction set. Do not enable auto-verification. Complete the missing fact strata and
agency-source coverage, real temporal validation and source/issuer/currentness proof before
re-evaluating the nationwide gate. Keep image PDFs blocked until real OCR is validated.
