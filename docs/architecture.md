# Architecture

## Goals

1. Represent every identifiable U.S. state and local law-enforcement agency as a canonical
   entity with explicit, reviewable links to external registries.
2. Represent radio-protocol knowledge (codes, phonetics, callsigns, procedures, ordered
   structures, interoperability rules, protocol modes) as **facts with provenance**.
3. Make "UNKNOWN" a first-class, durable value.
4. Run locally with no managed infrastructure, migrate to PostgreSQL without a schema redesign.

## Stack

* Python 3.12, `uv` for packaging, `pydantic` v2 models, `typer` CLI, `httpx`, `pypdf`,
  `selectolax`, `rapidfuzz`, `pytest`, `ruff`.
* Persistence: SQLite (`data/intermediate/corpus.sqlite`), one JSON payload column per
  table plus a few indexed columns. The SQL in `store/schema.sql` is portable; the
  PostgreSQL migration is JSON→JSONB and TEXT timestamps→TIMESTAMPTZ.
* Intermediate/normalized artifacts: JSONL under `data/normalized/`.
* No queues, no services, no containers.

## Data model (see docs/schema.md)

```
RegistryRecord --(AgencyLink: identity|subunit, confirmed|proposed|ambiguous)--> Agency
Agency --< DocumentLead --(acquire)--> Source --< DocumentRecord
Source --< ProtocolFact (fact_type, key, value, locator, excerpt, dates, confidence, statuses)
ProtocolFact >-- Conflict (fact_ids, kind, resolution, preferred_fact_id)
ProtocolFact / Agency --> EligibilityDecision (state, reasons, supporting sources, conflicts)
TrainingItem (future) --> fact_ids + source_ids (mandatory, non-empty)
```

## Pipeline stages

| # | stage | module | deterministic? | resumable key |
|---|---|---|---|---|
| 1 | registry ingestion | `registry/ingest.py` | yes | (dated registry, external_id); changed payload rejected |
| 2 | entity normalization + resolution | `registry/resolve.py` | yes | confirmed links skip |
| 3 | official-domain discovery | `discovery/stage.py` | yes (classifier); search input recorded | stage_progress(agency) |
| 4 | document discovery | same | yes | same |
| 5 | acquisition | `acquisition/fetch.py` | yes | lead.acquisition_status |
| 6 | text extraction | `extraction/text.py` | yes | stage_progress(source_id, parser version, hash) |
| 7 | candidate fact extraction | `extraction/codes.py`, `phonetics.py`, `procedures.py`, `llm.py` | parsers yes; model optional and opt-in | same |
| 8 | validation | `validation/rules.py` | yes | status events |
| 9 | source cross-checking | `conflicts/detect.py` | yes | conflict_id stable |
| 10 | conflict detection/resolution | same | yes | same |
| 11 | confidence/review + eligibility | `eligibility/policy.py` | yes | policy_version |
| 12 | normalized output + stats + invariants | `export.py`, `stats.py`, `invariants.py` | yes | – |

Every stage writes a `StageRun` row (stage, input fingerprint, stats, status). Item-level
checkpoints live in `stage_progress` so an interrupted run resumes without redoing work;
`--force` re-processes.

## Append-only evidence

`sources`, `documents` and `facts` are insert-only. `insert_fact` with an existing id is a
no-op. Status fields (verification, review, temporal, superseded_by) change only through
`record_fact_status` / `update_source_status`, which write `fact_events` / `source_events`
rows with a reason and run id. A newer extraction that disagrees with an older one produces a
**conflict**, never an overwrite.

## Model-backed extraction

`extraction/llm.py` defines an `Extractor` protocol. The default is `NullExtractor`.
`AnthropicExtractor` exists behind two explicit opt-ins (`RADIOCORPUS_ENABLE_MODEL_EXTRACTION=1`
and an API key), records the model id on every candidate, drops any candidate without a
known locator and excerpt, and can only ever produce `UNVERIFIED` / `NEEDS_REVIEW` facts. The
`ProtocolFact` validator refuses a model-extracted fact marked VERIFIED unless
`review_status == human_accepted`.

## Search providers

Discovery is driven by a `SearchProvider` interface. The build session had no direct
search-API access from the container, so the canary used `RecordedSearchProvider`, which
replays JSONL search results recorded verbatim by search-tool workers (query, rank, title,
URL, timestamp). `HttpSearchProvider` is a stub for a JSON search endpoint. Either way the
classifier (`discovery/classify.py`) is deterministic code; the search results are inputs,
never conclusions.

## Observability

`radiocorpus stats` produces the metric set required by the sprint; `run-canary` writes
`data/normalized/stats_{canary,fixtures,all}.json`. `check-invariants` exits non-zero on any
violation of corpus invariants, committed-snapshot checks or generated-report consistency.
Playback also requires structured human review, issuer/applicability evidence, confirmed
currentness with a recheck deadline, and matching acquired bytes; see source-policy.md.
