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

## Status (independent hardening audit, 2026-09-20)

Nationwide discovery remains blocked. The original Miami website assignment was
South Miami's website. All 59 legacy search-only assignments are quarantined.
Currentness, independence and cross-agency applicability now require explicit evidence.

The bounded sample attempted 20 agencies. Fourteen responses were captured (including
two unusable responses); six PDFs and HTML were exercised. The audit compared 116
candidates from four documents: 24 complete facts supported, zero learner-safe facts.
This was agent source review, not human acceptance. See [the audit](docs/hardening-audit.md)
and [generated metrics](docs/real-source-metrics.md) for limitations and remaining gates.
The 2018 registry remains a historical snapshot; it was not silently replaced.

Extraction was then rebuilt around a position-aware layout representation, because the
audited failures were structural: a revision date read as an eleven-code, section headings
read as a phonetic alphabet, and adjacent table columns bleeding into each other. Code,
phonetic and procedure parsers now require structural evidence before emitting anything.
Parser status is **EXTRACTION_NOT_READY**: all four real validation documents are refused by
the network egress policy, so precision on real documents is unmeasured and none was
substituted. See [layout extraction](docs/layout-extraction.md),
[extraction metrics](docs/extraction-metrics.md) and the
[audit handoff](docs/handoff-astra.md).

## Quick start

```bash
uv sync                       # Python 3.12, all dependencies
uv run pytest                 # offline regression suite
uv run radiocorpus check-invariants # checks database, committed JSONL and generated reports
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
