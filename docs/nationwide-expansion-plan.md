# Nationwide expansion remains blocked

The foundation readiness assessment is superseded by the independent
[hardening audit](hardening-audit.md). Do not start nationwide discovery or ingestion.
The old age-window, domain and corroboration assumptions were unsafe.

Required next gates: layout-aware real extraction, complete stratified source review,
current-policy evidence, real temporal-pair testing, registry currency validation and
independent review of the stacked hardening PR. Scanned documents remain explicitly
gated. The commands below are bounded research operations, not authorization to scale.

## Blocked operations and their reproduction commands

```bash
# 1. Acquire the 139 official candidate leads already discovered (resumes only blocked/pending)
uv run radiocorpus acquire
uv run radiocorpus extract && uv run radiocorpus classify-sources && uv run radiocorpus validate \
  && uv run radiocorpus crosscheck && uv run radiocorpus assign && uv run radiocorpus export \
  && uv run radiocorpus check-invariants && uv run radiocorpus canary-report

# 2. Re-run discovery for the 31 unsearched canary agencies (any search tool; append verbatim
#    records to data/canary/discovery_leads.jsonl following scratchpad protocol in
#    docs/research-methodology.md §3), then:
uv run radiocorpus discover --force
```

Agencies needing search (canary ids): S33/S41/S49 (search C only), S34/S42/S50 (C only),
S46 (B, C), NY/SC (C only), plus all searches for M01, M04, M06, M07, M09, M12, M14, M15,
M16, M17, M20, H02, H03, H04, H05, H08, H10, X01, X02, X03, X06, X08, X09, X10, X11, X14,
X16, X17, X18, X19, S48.

```bash
# 3. Load BJS registries once downloaded (ICPSR login required; accept terms manually)
#    place file + sidecar, e.g. data/raw/csllea_2018/csllea2018.tsv and csllea2018.tsv.map.json
uv run radiocorpus ingest-registry delimited data/raw/csllea_2018/csllea2018.tsv
uv run radiocorpus resolve --registry CSLLEA_2018

# 4. Live FBI agencies API (needs api.data.gov key) — adapter to add: registry/adapters/fbi_cde_api.py
#    GET https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}?API_KEY=...
```

## Phased plan

**Phase A — validate parsers on real documents (1–2 days with network).** Acquire the 139
canary leads. Expect PDFs with scanned pages (add OCR via `pypdf` + tesseract only if text
extraction yields < 200 chars/page), HTML policy portals (PowerDMS public portals are on the
non-official host list; agency-hosted mirrors are preferred), and non-radio documents that
matched on words like "communications" (expected precision of the title classifier is low;
the extraction stage simply yields zero facts for them).

**Phase B — finish the canary.** Search the remaining 31 agencies, acquire, extract. Produce
the first real per-agency coverage numbers. Add human review of every `proposed` registry
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
