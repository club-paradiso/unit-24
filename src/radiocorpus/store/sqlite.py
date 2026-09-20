"""Thin persistence layer over SQLite.

Design rules:
* Pydantic models are the source of truth; each table stores a JSON payload plus a few
  indexed columns copied from it.
* Evidence (sources, documents, facts) is append-only. `insert_fact` with an existing
  fact_id is a no-op (idempotent), never an overwrite. Status transitions go through
  `record_fact_status` which writes an audit event.
* No ORM. The SQL is small enough to read, and portable to PostgreSQL.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from radiocorpus.models import (
    Agency,
    AgencyLink,
    Conflict,
    DocumentLead,
    DocumentRecord,
    EligibilityDecision,
    ProtocolFact,
    RegistryRecord,
    Source,
    StageRun,
)
from radiocorpus.models.common import ReviewStatus, VerificationStatus

_SCHEMA = Path(__file__).with_name("schema.sql").read_text()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _dump(m: BaseModel) -> str:
    return m.model_dump_json()


class Store:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = ":memory:" if path is None else str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL") if self.path != ":memory:" else None
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(_SCHEMA)

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ---------------- registry records ----------------
    def upsert_registry_record(self, rec: RegistryRecord, run_id: str | None = None) -> bool:
        """Insert if absent. Returns True if inserted. Existing rows are never modified —
        a registry re-ingest with changed content is a new registry code (dated snapshot)."""
        existing = self.conn.execute(
            "SELECT payload FROM registry_records WHERE registry=? AND external_id=?", (rec.registry, rec.external_id)
        ).fetchone()
        if existing:
            old = RegistryRecord.model_validate_json(existing["payload"])
            if old.model_dump(exclude={"ingested_at"}) != rec.model_dump(exclude={"ingested_at"}):
                raise ValueError("registry snapshot collision: use a new dated registry code for changed content")
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO registry_records(registry, external_id, payload, ingested_at, run_id) VALUES (?,?,?,?,?)",
            (rec.registry, rec.external_id, _dump(rec), rec.ingested_at.isoformat(), run_id),
        )
        return cur.rowcount == 1

    def registry_records(self, registry: str | None = None) -> Iterator[RegistryRecord]:
        q = "SELECT payload FROM registry_records" + (" WHERE registry=?" if registry else "")
        for row in self.conn.execute(q, (registry,) if registry else ()):
            yield RegistryRecord.model_validate_json(row["payload"])

    def registry_count(self, registry: str | None = None) -> int:
        q = "SELECT COUNT(*) FROM registry_records" + (" WHERE registry=?" if registry else "")
        return int(self.conn.execute(q, (registry,) if registry else ()).fetchone()[0])

    # ---------------- agencies ----------------
    def upsert_agency(self, a: Agency) -> None:
        self.conn.execute(
            """INSERT INTO agencies(agency_id, canonical_name, state, agency_type, research_status, is_fixture, payload, updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(agency_id) DO UPDATE SET canonical_name=excluded.canonical_name, state=excluded.state,
               agency_type=excluded.agency_type, research_status=excluded.research_status, is_fixture=excluded.is_fixture,
               payload=excluded.payload, updated_at=excluded.updated_at""",
            (a.agency_id, a.canonical_name, a.state, a.agency_type, a.research_status, int(a.is_fixture), _dump(a), _now()),
        )

    def get_agency(self, agency_id: str) -> Agency | None:
        row = self.conn.execute("SELECT payload FROM agencies WHERE agency_id=?", (agency_id,)).fetchone()
        return Agency.model_validate_json(row["payload"]) if row else None

    def agencies(self, *, state: str | None = None, include_fixtures: bool = False) -> Iterator[Agency]:
        q = "SELECT payload FROM agencies WHERE 1=1"
        args: list[Any] = []
        if state:
            q += " AND state=?"
            args.append(state)
        if not include_fixtures:
            q += " AND is_fixture=0"
        for row in self.conn.execute(q + " ORDER BY agency_id", args):
            yield Agency.model_validate_json(row["payload"])

    def agency_count(self, include_fixtures: bool = False) -> int:
        q = "SELECT COUNT(*) FROM agencies" + ("" if include_fixtures else " WHERE is_fixture=0")
        return int(self.conn.execute(q).fetchone()[0])

    def find_agencies_by_name(self, state: str | None, name_like: str) -> list[Agency]:
        q = "SELECT payload FROM agencies WHERE canonical_name LIKE ?" + (" AND state=?" if state else "")
        args = [f"%{name_like}%"] + ([state] if state else [])
        return [Agency.model_validate_json(r["payload"]) for r in self.conn.execute(q, args)]

    # ---------------- links ----------------
    def upsert_link(self, link: AgencyLink) -> None:
        self.conn.execute(
            """INSERT INTO agency_links(link_id, agency_id, registry, external_id, link_kind, status, payload) VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(link_id) DO UPDATE SET status=excluded.status, payload=excluded.payload""",
            (link.link_id, link.agency_id, link.registry, link.external_id, link.link_kind, link.status, _dump(link)),
        )

    def links(self, agency_id: str | None = None, status: str | None = None) -> list[AgencyLink]:
        q = "SELECT payload FROM agency_links WHERE 1=1"
        args: list[Any] = []
        if agency_id:
            q += " AND agency_id=?"
            args.append(agency_id)
        if status:
            q += " AND status=?"
            args.append(status)
        return [AgencyLink.model_validate_json(r["payload"]) for r in self.conn.execute(q, args)]

    def links_for_record(self, registry: str, external_id: str) -> list[AgencyLink]:
        return [
            AgencyLink.model_validate_json(r["payload"])
            for r in self.conn.execute("SELECT payload FROM agency_links WHERE registry=? AND external_id=?", (registry, external_id))
        ]

    # ---------------- leads ----------------
    def upsert_lead(self, lead: DocumentLead) -> None:
        self.conn.execute(
            """INSERT INTO document_leads(lead_id, agency_id, url, host, lead_class, acquisition_status, payload, updated_at) VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(lead_id) DO UPDATE SET lead_class=excluded.lead_class, acquisition_status=excluded.acquisition_status,
               payload=excluded.payload, updated_at=excluded.updated_at""",
            (lead.lead_id, lead.agency_id, lead.url, lead.host, lead.lead_class, lead.acquisition_status, _dump(lead), _now()),
        )

    def leads(self, agency_id: str | None = None) -> list[DocumentLead]:
        q = "SELECT payload FROM document_leads" + (" WHERE agency_id=?" if agency_id else "") + " ORDER BY lead_id"
        return [DocumentLead.model_validate_json(r["payload"]) for r in self.conn.execute(q, (agency_id,) if agency_id else ())]

    # ---------------- sources / documents ----------------
    def insert_source(self, s: Source) -> bool:
        cur = self.conn.execute(
            """INSERT OR IGNORE INTO sources(source_id, canonical_url, document_hash, source_type, source_quality, temporal_status,
               agency_or_jurisdiction, is_fixture, payload, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                s.source_id,
                s.canonical_url,
                s.document_hash,
                s.source_type,
                s.source_quality,
                s.temporal_status,
                s.agency_or_jurisdiction,
                int(s.is_fixture),
                _dump(s),
                _now(),
            ),
        )
        return cur.rowcount == 1

    def get_source(self, source_id: str) -> Source | None:
        row = self.conn.execute("SELECT payload FROM sources WHERE source_id=?", (source_id,)).fetchone()
        return Source.model_validate_json(row["payload"]) if row else None

    def sources(self, agency_id: str | None = None, include_fixtures: bool = True) -> list[Source]:
        q = "SELECT payload FROM sources WHERE 1=1"
        args: list[Any] = []
        if agency_id:
            q += " AND agency_or_jurisdiction=?"
            args.append(agency_id)
        if not include_fixtures:
            q += " AND is_fixture=0"
        return [Source.model_validate_json(r["payload"]) for r in self.conn.execute(q + " ORDER BY source_id", args)]

    def update_source_status(self, source_id: str, *, field: str, new_value: str, reason: str, run_id: str | None = None) -> None:
        """The only mutable source fields are classification fields (quality, temporal status,
        supersedes links). Every change is audited in source_events."""
        s = self.get_source(source_id)
        if s is None:
            raise KeyError(source_id)
        allowed = {
            "source_quality",
            "temporal_status",
            "superseded_by",
            "supersedes",
            "effective_date",
            "publication_date",
            "revision",
            "currentness",
            "currentness_evidence",
            "identity_evidence",
            "host_matches_target_entity",
            "host_is_government",
            "applicability",
            "evidence_lineage",
            "issuing_authority_id",
            "issuing_authority_evidence",
        }
        if field not in allowed:
            raise ValueError(f"field {field} is immutable on sources")
        old = getattr(s, field)
        s2 = Source.model_validate({**s.model_dump(), field: new_value})
        self.conn.execute(
            "UPDATE sources SET source_quality=?, temporal_status=?, payload=? WHERE source_id=?",
            (s2.source_quality, s2.temporal_status, _dump(s2), source_id),
        )
        self.conn.execute(
            "INSERT INTO source_events(source_id, field, old_value, new_value, reason, run_id, at) VALUES (?,?,?,?,?,?,?)",
            (source_id, field, str(old) if old is not None else None, str(new_value), reason, run_id, _now()),
        )

    def insert_document(self, d: DocumentRecord) -> bool:
        cur = self.conn.execute(
            """INSERT OR IGNORE INTO documents(document_hash, source_id, local_path, text_path, content_type, byte_length, page_count, payload)
               VALUES (?,?,?,?,?,?,?,?)""",
            (d.document_hash, d.source_id, d.local_path, d.text_path, d.content_type, d.byte_length, d.page_count, _dump(d)),
        )
        return cur.rowcount == 1

    def get_document(self, document_hash: str) -> DocumentRecord | None:
        row = self.conn.execute("SELECT payload FROM documents WHERE document_hash=?", (document_hash,)).fetchone()
        return DocumentRecord.model_validate_json(row["payload"]) if row else None

    def documents(self) -> list[DocumentRecord]:
        return [DocumentRecord.model_validate_json(r["payload"]) for r in self.conn.execute("SELECT payload FROM documents ORDER BY document_hash")]

    # ---------------- facts ----------------
    def insert_fact(self, f: ProtocolFact) -> bool:
        """Append-only. Returns False if the fact_id already exists (never overwrites)."""
        cur = self.conn.execute(
            """INSERT OR IGNORE INTO facts(fact_id, agency_id, fact_type, key, source_id, verification_status, review_status,
               temporal_status, extraction_method, payload, created_at, run_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                f.fact_id,
                f.agency_id,
                f.fact_type,
                f.key,
                f.source_id,
                f.verification_status,
                f.review_status,
                f.temporal_status,
                f.extraction_method,
                _dump(f),
                f.created_at.isoformat(),
                f.run_id,
            ),
        )
        return cur.rowcount == 1

    def get_fact(self, fact_id: str) -> ProtocolFact | None:
        row = self.conn.execute("SELECT payload FROM facts WHERE fact_id=?", (fact_id,)).fetchone()
        return ProtocolFact.model_validate_json(row["payload"]) if row else None

    def facts(self, agency_id: str | None = None, fact_type: str | None = None) -> list[ProtocolFact]:
        q = "SELECT payload FROM facts WHERE 1=1"
        args: list[Any] = []
        if agency_id:
            q += " AND agency_id=?"
            args.append(agency_id)
        if fact_type:
            q += " AND fact_type=?"
            args.append(fact_type)
        return [ProtocolFact.model_validate_json(r["payload"]) for r in self.conn.execute(q + " ORDER BY fact_id", args)]

    def record_fact_status(
        self,
        fact_id: str,
        *,
        verification_status: VerificationStatus | None = None,
        review_status: ReviewStatus | None = None,
        review_evidence: dict | None = None,
        temporal_status: str | None = None,
        superseded_by: str | None = None,
        reason: str,
        run_id: str | None = None,
    ) -> ProtocolFact:
        f = self.get_fact(fact_id)
        if f is None:
            raise KeyError(fact_id)
        updates: dict[str, Any] = {}
        if review_evidence is not None:
            updates["review_evidence"] = review_evidence
        if verification_status is not None and verification_status != f.verification_status:
            updates["verification_status"] = verification_status
        if review_status is not None and review_status != f.review_status:
            updates["review_status"] = review_status
        if temporal_status is not None and temporal_status != f.temporal_status:
            updates["temporal_status"] = temporal_status
        if superseded_by is not None and superseded_by != f.superseded_by:
            updates["superseded_by"] = superseded_by
        if not updates:
            return f
        f2 = ProtocolFact.model_validate({**f.model_dump(), **updates})
        for k, v in updates.items():
            self.conn.execute(
                "INSERT INTO fact_events(fact_id, field, old_value, new_value, reason, run_id, at) VALUES (?,?,?,?,?,?,?)",
                (fact_id, k, str(getattr(f, k)), str(v), reason, run_id, _now()),
            )
        self.conn.execute(
            "UPDATE facts SET verification_status=?, review_status=?, temporal_status=?, payload=? WHERE fact_id=?",
            (f2.verification_status, f2.review_status, f2.temporal_status, _dump(f2), fact_id),
        )
        return f2

    def fact_events(self, fact_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM fact_events WHERE fact_id=? ORDER BY id", (fact_id,))]

    # ---------------- conflicts ----------------
    def upsert_conflict(self, c: Conflict) -> None:
        self.conn.execute(
            """INSERT INTO conflicts(conflict_id, agency_id, fact_type, key, kind, resolution, payload, updated_at) VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(conflict_id) DO UPDATE SET resolution=excluded.resolution, payload=excluded.payload, updated_at=excluded.updated_at""",
            (c.conflict_id, c.agency_id, c.fact_type, c.key, c.kind, c.resolution, _dump(c), _now()),
        )

    def conflicts(self, agency_id: str | None = None) -> list[Conflict]:
        q = "SELECT payload FROM conflicts" + (" WHERE agency_id=?" if agency_id else "") + " ORDER BY conflict_id"
        return [Conflict.model_validate_json(r["payload"]) for r in self.conn.execute(q, (agency_id,) if agency_id else ())]

    # ---------------- eligibility ----------------
    def upsert_eligibility(self, e: EligibilityDecision) -> None:
        self.conn.execute(
            """INSERT INTO eligibility(subject_kind, subject_id, state, policy_version, payload, decided_at) VALUES (?,?,?,?,?,?)
               ON CONFLICT(subject_kind, subject_id) DO UPDATE SET state=excluded.state, policy_version=excluded.policy_version,
               payload=excluded.payload, decided_at=excluded.decided_at""",
            (e.subject_kind, e.subject_id, e.state, e.policy_version, _dump(e), _now()),
        )

    def eligibility(self, subject_kind: str | None = None) -> list[EligibilityDecision]:
        q = "SELECT payload FROM eligibility" + (" WHERE subject_kind=?" if subject_kind else "")
        return [EligibilityDecision.model_validate_json(r["payload"]) for r in self.conn.execute(q, (subject_kind,) if subject_kind else ())]

    # ---------------- runs / progress ----------------
    def save_run(self, r: StageRun) -> None:
        self.conn.execute(
            """INSERT INTO runs(run_id, stage, input_fingerprint, status, payload) VALUES (?,?,?,?,?)
               ON CONFLICT(run_id) DO UPDATE SET status=excluded.status, payload=excluded.payload""",
            (r.run_id, r.stage, r.input_fingerprint, r.status, _dump(r)),
        )

    def runs(self) -> list[StageRun]:
        return [StageRun.model_validate_json(r["payload"]) for r in self.conn.execute("SELECT payload FROM runs ORDER BY run_id")]

    def progress_done(self, stage: str, item_key: str, fingerprint: str) -> bool:
        row = self.conn.execute("SELECT status, input_fingerprint FROM stage_progress WHERE stage=? AND item_key=?", (stage, item_key)).fetchone()
        return bool(row) and row["status"] == "done" and row["input_fingerprint"] == fingerprint

    def mark_progress(self, stage: str, item_key: str, fingerprint: str, status: str, run_id: str, note: str | None = None) -> None:
        self.conn.execute(
            """INSERT INTO stage_progress(stage, item_key, input_fingerprint, status, run_id, note, updated_at) VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(stage, item_key) DO UPDATE SET input_fingerprint=excluded.input_fingerprint, status=excluded.status,
               run_id=excluded.run_id, note=excluded.note, updated_at=excluded.updated_at""",
            (stage, item_key, fingerprint, status, run_id, note, _now()),
        )

    def progress_rows(self, stage: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM stage_progress WHERE stage=?", (stage,))]

    # ---------------- generic helpers ----------------
    def count(self, table: str, where: str = "1=1", args: Iterable[Any] = ()) -> int:
        return int(self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", tuple(args)).fetchone()[0])

    def raw(self, sql: str, args: Iterable[Any] = ()) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(sql, tuple(args))]

    def commit(self) -> None:
        self.conn.commit()


def dump_jsonl(rows: Iterable[BaseModel], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(json.loads(r.model_dump_json()), sort_keys=True) + "\n")
            n += 1
    return n
