# ADR 0001 — SQLite with JSON payload columns; no ORM

**Status:** accepted (2026-09-20)

**Context.** The pipeline must run locally without managed infrastructure and migrate to
PostgreSQL later. Models are pydantic and evolve during research.

**Decision.** Persist every model as a JSON payload column plus the few columns we index or
join on. Hand-written SQL in `store/schema.sql`; a thin `Store` class; no ORM.

**Consequences.** Schema evolution is a pydantic change, not a migration, until columns are
promoted. PostgreSQL migration = JSON→JSONB + timestamp types + the same SQL. Queries across
payload fields use `json_extract`, which is adequate at ~10^5 rows.
