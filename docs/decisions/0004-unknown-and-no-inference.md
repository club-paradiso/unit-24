> Historical foundation decision. Currentness and review semantics are superseded by [0005](0005-explicit-evidence.md).

# ADR 0004 — UNKNOWN is a value; no inference across agencies; append-only evidence

**Status:** accepted (2026-09-20)

**Decision.**
* Optional fields are `None` = UNKNOWN; enumerations carry explicit `unknown`.
* A fact cites exactly one source attributed to the fact's own agency (or its documented
  parent/dispatch provider). Invariant `no_cross_agency_synthesis` enforces this.
* Sources, documents and facts are insert-only; status transitions are audited events.
  Disagreement between extractions becomes a `Conflict`, never an overwrite.
* Official quality requires a hashed document; undated official = partial, never current.
* Model output is never verified without human acceptance (validator + policy + invariant).
