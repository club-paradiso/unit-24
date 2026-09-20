# US Public Safety Radio Protocol Corpus

Research and data infrastructure for an English-learning product that trains listeners to
understand and respond to U.S. public-safety radio traffic. This repository is the **data
layer only**: a canonical agency registry, a provenance-first radio-protocol knowledge model,
and a reproducible research pipeline. There is no learner-facing application here.

## Core principle

> A missing fact stays **UNKNOWN**. Nothing agency-specific is ever inferred from a
> neighbouring agency, a shared dispatch centre, a state agency, or "common practice".
> Every playable fact traces to a hashed source document, a locator inside it, and a short
> excerpt.

## Status (foundation sprint, 2026-09-20)

| area | state |
|---|---|
| Canonical registry | 23,243 FBI UCR reporting units (2018-06-28 snapshot) + 100 curated canary agencies, resolved with confirmed / proposed / ambiguous links |
| Protocol schema | 8 fact types, evidence objects, conflicts, eligibility; JSON Schema in `schemas/` |
| Pipeline | 12 stages, resumable and idempotent, SQLite-backed, `radiocorpus run-canary` reproduces everything |
| Tests | 61 passing (`uv run pytest`), 8 corpus invariants enforced |
| Canary discovery | 100 / 100 agencies searched (two rounds; the first hit the session search budget), 78 official domains, 136 official radio-policy leads across 57 agencies |
| Canary acquisition | **0 documents acquired**: every government/agency host was blocked by the build environment's egress policy (232 leads recorded as `blocked_egress`) |
| Extraction / conflicts / eligibility | Exercised end-to-end on a synthetic fixture corpus (7 documents, 89 facts, 3 conflicts) |

See `docs/canary-report.md` for the per-agency table and `docs/nationwide-expansion-plan.md`
for what happens next.

## Quick start

```bash
uv sync                       # Python 3.12, all dependencies
uv run pytest                 # 61 tests
uv run radiocorpus run-canary # full pipeline -> data/intermediate/corpus.sqlite, data/normalized/, docs/canary-report.md
uv run radiocorpus check-invariants
uv run radiocorpus explain <fact_id>   # "why is this the expected answer?" from evidence only
```

Individual stages (`ingest-registry`, `resolve`, `discover`, `acquire`, `extract`,
`classify-sources`, `validate`, `crosscheck`, `assign`, `export`, `stats`) can be run
separately; each is resumable and safe to re-run.

## Layout

```
src/radiocorpus/
  models/        pydantic models: agency, source/lead/document, fact, conflict, eligibility, run
  store/         SQLite persistence (append-only evidence, audited status changes)
  registry/      registry adapters + entity resolution
  discovery/     search providers, lead classification, domain/document discovery
  acquisition/   robots-aware fetching, content-addressed storage
  extraction/    text extraction, deterministic code/phonetic/procedure parsers, model extractor interface
  normalization/ name, state, date normalisation
  validation/    deterministic fact validation
  provenance/    source quality + temporal classification
  conflicts/     cross-source conflict detection and evidence-based resolution
  eligibility/   verification + training-eligibility policy, explain()
  stats.py invariants.py report.py export.py cli.py
schemas/         JSON Schema per persisted model
tests/           pytest suite
data/
  raw/           dated registry snapshots (+ MANIFEST), acquired documents (git-ignored)
  canary/        canary seed (100 agencies) and recorded discovery results
  fixtures/      synthetic documents (state ZZ, fictional agencies)
  intermediate/  corpus.sqlite (git-ignored)
  normalized/    JSONL exports + stats
docs/            architecture, methodology, source policy, schema, canary, expansion plan, decisions/
```

## Scope and ethics

Only lawfully accessible public information is used. The fetcher honours robots.txt, never
authenticates, never retries a 403, and never circumvents CAPTCHAs, paywalls or technical
restrictions. The corpus models static, publicly documented communication protocol for
language education; it contains nothing that enables live tracking, evasion, surveillance,
or interference with emergency communications.
