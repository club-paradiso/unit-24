"""Deterministic identifier generation.

All identifiers are derived from stable natural keys so that re-running ingestion is
idempotent: the same input always yields the same id, and nothing depends on insertion
order or wall-clock time.
"""

from __future__ import annotations

import hashlib


def _digest(*parts: str, n: int = 16) -> str:
    h = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return h[:n]


def agency_id(namespace: str, key: str) -> str:
    """namespace: registry code (e.g. FBI_CDE_FRONTEND_2018, CURATED); key: external id."""
    return f"agy_{_digest('agency', namespace, key)}"


def source_id(canonical_url: str, document_hash: str | None = None) -> str:
    return f"src_{_digest('source', canonical_url, document_hash or '')}"


def lead_id(agency: str, url: str, query: str) -> str:
    return f"lead_{_digest('lead', agency, url, query)}"


def fact_id(agency: str, fact_type: str, key: str, source: str, locator: str, value_fingerprint: str) -> str:
    return f"fct_{_digest('fact', agency, fact_type, key, source, locator, value_fingerprint)}"


def conflict_id(agency: str, fact_type: str, key: str, fact_ids: list[str]) -> str:
    return f"cfl_{_digest('conflict', agency, fact_type, key, *sorted(fact_ids))}"


def link_id(agency: str, registry: str, external_id: str) -> str:
    return f"lnk_{_digest('link', agency, registry, external_id)}"


def run_id(stage: str, fingerprint: str) -> str:
    return f"run_{stage}_{_digest('run', stage, fingerprint, n=10)}"


def document_hash(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()
