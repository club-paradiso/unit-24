-- SQLite schema. Kept deliberately portable (no SQLite-only types) so migration to
-- PostgreSQL is a matter of JSON -> JSONB and TEXT timestamps -> TIMESTAMPTZ.
-- Evidence tables (sources, documents, facts) are append-only: rows are inserted, never
-- updated in place; status transitions are recorded in *_events tables.

CREATE TABLE IF NOT EXISTS registry_records (
  registry TEXT NOT NULL,
  external_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  run_id TEXT,
  PRIMARY KEY (registry, external_id)
);

CREATE TABLE IF NOT EXISTS agencies (
  agency_id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  state TEXT,
  agency_type TEXT NOT NULL,
  research_status TEXT NOT NULL,
  is_fixture INTEGER NOT NULL DEFAULT 0,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_agencies_state ON agencies(state);
CREATE INDEX IF NOT EXISTS ix_agencies_name ON agencies(canonical_name);

CREATE TABLE IF NOT EXISTS agency_links (
  link_id TEXT PRIMARY KEY,
  agency_id TEXT NOT NULL,
  registry TEXT NOT NULL,
  external_id TEXT NOT NULL,
  link_kind TEXT NOT NULL,
  status TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_links_reg ON agency_links(registry, external_id);
CREATE INDEX IF NOT EXISTS ix_links_agency ON agency_links(agency_id);

CREATE TABLE IF NOT EXISTS document_leads (
  lead_id TEXT PRIMARY KEY,
  agency_id TEXT NOT NULL,
  url TEXT NOT NULL,
  host TEXT NOT NULL,
  lead_class TEXT NOT NULL,
  acquisition_status TEXT NOT NULL,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_leads_agency ON document_leads(agency_id);

CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  canonical_url TEXT NOT NULL,
  document_hash TEXT,
  source_type TEXT NOT NULL,
  source_quality TEXT NOT NULL,
  temporal_status TEXT NOT NULL,
  agency_or_jurisdiction TEXT,
  is_fixture INTEGER NOT NULL DEFAULT 0,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sources_agency ON sources(agency_or_jurisdiction);

CREATE TABLE IF NOT EXISTS source_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL,
  field TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  reason TEXT NOT NULL,
  run_id TEXT,
  at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
  document_hash TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  local_path TEXT NOT NULL,
  text_path TEXT,
  content_type TEXT,
  byte_length INTEGER NOT NULL,
  page_count INTEGER,
  payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS facts (
  fact_id TEXT PRIMARY KEY,
  agency_id TEXT NOT NULL,
  fact_type TEXT NOT NULL,
  key TEXT NOT NULL,
  source_id TEXT NOT NULL,
  verification_status TEXT NOT NULL,
  review_status TEXT NOT NULL,
  temporal_status TEXT NOT NULL,
  extraction_method TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  run_id TEXT
);
CREATE INDEX IF NOT EXISTS ix_facts_agency ON facts(agency_id, fact_type, key);
CREATE INDEX IF NOT EXISTS ix_facts_source ON facts(source_id);

CREATE TABLE IF NOT EXISTS fact_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fact_id TEXT NOT NULL,
  field TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  reason TEXT NOT NULL,
  run_id TEXT,
  at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conflicts (
  conflict_id TEXT PRIMARY KEY,
  agency_id TEXT NOT NULL,
  fact_type TEXT NOT NULL,
  key TEXT NOT NULL,
  kind TEXT NOT NULL,
  resolution TEXT NOT NULL,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eligibility (
  subject_kind TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  state TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  payload TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  PRIMARY KEY (subject_kind, subject_id)
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  stage TEXT NOT NULL,
  input_fingerprint TEXT NOT NULL,
  status TEXT NOT NULL,
  payload TEXT NOT NULL
);

-- Per-item checkpoints make stages resumable: an item completed in a previous run of the
-- same stage with the same input fingerprint is skipped unless --force.
CREATE TABLE IF NOT EXISTS stage_progress (
  stage TEXT NOT NULL,
  item_key TEXT NOT NULL,
  input_fingerprint TEXT NOT NULL,
  status TEXT NOT NULL,
  run_id TEXT NOT NULL,
  note TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (stage, item_key)
);
