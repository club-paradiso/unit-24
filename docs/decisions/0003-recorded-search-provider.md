# ADR 0003 — Discovery from recorded search results behind a provider interface

**Status:** accepted (2026-09-20)

**Context.** The container had no search API access; the session's search tool was
available to workers with a hard budget (200 calls/session) and returned titles + URLs only.

**Decision.** Define `SearchProvider`; implement `RecordedSearchProvider` that replays
verbatim JSONL records (query, rank, title, url, timestamp, engine) and distinguishes
"search not performed" from "no results". Classification of hosts and documents is
deterministic code. Add `HttpSearchProvider` as the production path.

**Consequences.** Discovery is reproducible from committed inputs. Worker judgment lines are
kept but never used to set fields. Coverage gaps are visible as `blocked`, not as absence.
