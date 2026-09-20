# Nationwide expansion plan and readiness gate

## Readiness gate (evaluated 2026-09-20)

| criterion | evidence | verdict |
|---|---|---|
| entity resolution behaves reliably | 54 exact confirmations, 1,183 sub-unit proposals, 10 fuzzy proposals, 0 ambiguous on 23,243 rows; trap cases (Berkeley PD vs UC Berkeley PD, Miami Beach vs Miami, Excise Police vs State Police, same-name different state) covered by tests; re-run changes nothing | **pass** |
| provenance survives end-to-end | every fact carries source_id + locator + excerpt; `explain` returns hash, URL, locator, excerpt, reasons; invariants 1, 7, 8 hold | **pass** (on fixtures; real documents not yet acquired) |
| UNKNOWN stays UNKNOWN | 22 canary agencies keep `official_website=None` after search; blocked ≠ no_public_source; neighbour-township fixture has no facts; invariant 6 holds | **pass** |
| conflicts preserved | 3 fixture conflicts stored with all participants; 1 unresolved; nothing deleted; invariant 5 holds | **pass** |
| current vs historical distinguishable | source quality/temporal status, superseded_by links, HISTORICAL_ONLY eligibility; invariant 3 holds | **pass** |
| extraction errors measurable | validation stats (`passed/rejected/problem:*`), per-fact confidence, per-document `stage_progress` notes | **pass** (measured on fixtures only) |
| retries/resumption work | item-level checkpoints; second `run-canary` skips all 100 agencies and 7 documents; acquisition resumes exactly the `blocked_egress` leads | **pass** |
| tests pass | 61/61, ruff clean | **pass** |

**Decision:** the schema and pipeline are ready for nationwide *registry ingestion and
discovery*. **However**, one operation was impossible in the build session and must run in
an environment with network access before any real fact enters the corpus: document
acquisition (all government/agency hosts egress-blocked).

Nationwide registry ingestion has effectively already happened (23,243 FBI reporting units
resolved). Nationwide *discovery* should start only after acquisition has been exercised on
the 232 canary leads, so that the extraction parsers are validated on real documents before
scaling.

## Blocked operations and their reproduction commands

```bash
# 1. Acquire the 232 official candidate leads already discovered (resumes only blocked/pending)
uv run radiocorpus acquire
uv run radiocorpus extract && uv run radiocorpus classify-sources && uv run radiocorpus validate \
  && uv run radiocorpus crosscheck && uv run radiocorpus assign && uv run radiocorpus export \
  && uv run radiocorpus check-invariants && uv run radiocorpus canary-report

# 2. (Optional) one skipped site: search remains: Maricopa County Sheriff's Office (CAN-H04) had no
#    agency-operated host in results; if www.maricopa.gov is accepted as its host, run search C
#    and append verbatim records to data/canary/discovery_leads.jsonl, then:
uv run radiocorpus discover --force
```

```bash
# 3. Load BJS registries once downloaded (ICPSR login required; accept terms manually)
#    place file + sidecar, e.g. data/raw/csllea_2018/csllea2018.tsv and csllea2018.tsv.map.json
uv run radiocorpus ingest-registry delimited data/raw/csllea_2018/csllea2018.tsv
uv run radiocorpus resolve --registry CSLLEA_2018

# 4. Live FBI agencies API (needs api.data.gov key) — adapter to add: registry/adapters/fbi_cde_api.py
#    GET https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}?API_KEY=...
```

## Phased plan

**Phase A — validate parsers on real documents (1–2 days with network).** Acquire the 232
canary leads. Expect PDFs with scanned pages (add OCR via `pypdf` + tesseract only if text
extraction yields < 200 chars/page), HTML policy portals (PowerDMS public portals are on the
non-official host list; agency-hosted mirrors are preferred), and non-radio documents that
matched on words like "communications" (expected precision of the title classifier is low;
the extraction stage simply yields zero facts for them).

**Phase B — finish the canary.** Extract from the acquired documents and produce the first
real per-agency coverage numbers. Add human review of every `proposed` registry
link for canary agencies and of every fact marked `needs_review`.

**Phase C — nationwide discovery (≈20k agencies).** Search provider: a JSON search API
(`HttpSearchProvider`) at roughly 2 queries per agency ≈ 40k queries; rate-limit and cache by
query hash. Prioritise: state agencies and large municipal/sheriff (done), then agencies with
FBI `agency_type_name` City/County by population proxy, then special jurisdictions. Every
agency without an official host after search A gets `research_status=discovery_started`
and is retried with the state POST directory as a second identity/website source.

**Phase D — registries.** Load CSLLEA 2018 and LEAR 2016 as new registry codes; run the
resolver against the canonical set; review `ambiguous`; retire FBI 2018 rows that CSLLEA
marks closed (status=inactive with valid_to, never deleted). Add the FBI live API adapter and
re-run yearly.

**Phase E — PostgreSQL.** When the corpus exceeds what a single SQLite file serves
comfortably (roughly >10^6 facts) or when an API needs concurrent writers, migrate: same
tables, JSON→JSONB, add GIN indexes on payload keys used by the app.

## Unresolved architectural risks

* **Document precision.** Title-based classification will over-fetch; real precision is
  unknown until Phase A. Mitigation: fetch is cheap, extraction yields zero facts on
  irrelevant documents, stats expose `documents_acquired` vs `agencies_with_code_data`.
* **Scanned PDFs / images.** No OCR in the pipeline yet. Facts from scanned manuals would
  be missed silently (they simply do not appear); track `page_count` vs extracted text length.
* **Procedure extraction is shallow.** The prescriptive-sentence spotter finds candidates at
  0.4 confidence; turning them into structured `procedure_rule` facts with prescribed
  phrases needs either human review or the model extractor plus review.
* **Dispatch-provider knowledge is empty.** `dispatch_provider` is UNKNOWN for all real
  agencies; the jurisdictional conflict rule therefore only fires on fixtures today.
* **Registry currency.** The only loaded nationwide roster is from 2018. Agencies created,
  renamed or merged since are missing or stale until CSLLEA/API loads.
* **Search-tool dependence.** Discovery quality depends on the search provider; the recorded
  provider is reproducible but not refreshable without a tool.
