"""Stage 5: document acquisition.

* Only leads classed as official/standards candidates are fetched.
* robots.txt is honoured; no auth, no CAPTCHA/paywall circumvention, no retries against 403.
* Bytes are stored content-addressed under data/raw/documents/<sha256>.<ext>. A re-fetch that
  yields different bytes produces a NEW source (new hash); the old one is never overwritten.
* Proxy/egress denials are recorded as BLOCKED_EGRESS with the reason, so a later run in an
  environment with access can resume exactly those leads.
"""

from __future__ import annotations

import mimetypes
from collections import Counter
from pathlib import Path

import httpx

from radiocorpus import ids
from radiocorpus.acquisition.robots import allowed
from radiocorpus.config import PATHS
from radiocorpus.models import DocumentLead, DocumentRecord, Source, StageRun
from radiocorpus.models.common import AcquisitionStatus, LeadClass, SourceQuality, SourceType, TemporalStatus, utcnow
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.store import Store

USER_AGENT = "radiocorpus-research/0.1 (+public-safety radio protocol corpus; contact via repository)"
FETCHABLE = {LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE, LeadClass.OFFICIAL_DOCUMENT_CANDIDATE, LeadClass.STANDARDS_BODY_DOCUMENT}
_EXT = {"application/pdf": ".pdf", "text/html": ".html", "text/plain": ".txt", "application/xhtml+xml": ".html"}


def _ext_for(content_type: str | None, url: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in _EXT:
        return _EXT[ct]
    guess = mimetypes.guess_extension(ct) if ct else None
    if guess:
        return guess
    return ".pdf" if url.lower().endswith(".pdf") else ".bin"


def store_bytes(data: bytes, content_type: str | None, url: str, doc_dir: Path) -> tuple[str, Path]:
    h = ids.document_hash(data)
    path = doc_dir / f"{h.split(':', 1)[1]}{_ext_for(content_type, url)}"
    doc_dir.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return h, path


def register_document(
    store: Store,
    lead: DocumentLead,
    data: bytes,
    content_type: str | None,
    *,
    doc_dir: Path,
    source_type: SourceType = SourceType.UNKNOWN,
    is_fixture: bool = False,
    title: str | None = None,
    issuing_authority: str | None = None,
) -> Source:
    h, path = store_bytes(data, content_type, lead.url, doc_dir)
    sid = ids.source_id(lead.url, h)
    src = Source(
        source_id=sid,
        source_type=source_type,
        title=title or lead.title,
        issuing_authority=issuing_authority,
        agency_or_jurisdiction=lead.agency_id,
        canonical_url=lead.url,
        original_file_url=lead.url,
        retrieved_at=utcnow(),
        document_hash=h,
        local_path=str(path.relative_to(PATHS.root)) if path.is_relative_to(PATHS.root) else str(path),
        content_type=content_type,
        source_quality=SourceQuality.UNVERIFIED,
        temporal_status=TemporalStatus.UNCERTAIN,
        is_fixture=is_fixture,
    )
    store.insert_source(src)
    store.insert_document(
        DocumentRecord(document_hash=h, source_id=sid, local_path=src.local_path or str(path), content_type=content_type, byte_length=len(data))
    )
    store.upsert_lead(lead.model_copy(update={"acquisition_status": AcquisitionStatus.FETCHED, "source_id": sid}))
    return src


def acquire(store: Store, *, doc_dir: Path | None = None, limit: int | None = None, force: bool = False, timeout: float = 30.0) -> StageRun:
    doc_dir = doc_dir or PATHS.documents
    leads = [lead for lead in store.leads() if lead.lead_class in FETCHABLE]
    fp = f"{len(leads)}:{doc_dir}"
    run = start_run(store, "acquisition", fp)
    stats: Counter[str] = Counter()
    client = httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=timeout, trust_env=True)
    n = 0
    try:
        for lead in leads:
            if limit is not None and n >= limit:
                break
            if not force and lead.acquisition_status == AcquisitionStatus.FETCHED:
                stats["already_fetched"] += 1
                continue
            n += 1
            status, note = _fetch_one(store, lead, client, doc_dir)
            stats[status] += 1
            if status != AcquisitionStatus.FETCHED:
                store.upsert_lead(lead.model_copy(update={"acquisition_status": status, "acquisition_note": note}))
            store.commit()
    finally:
        client.close()
    return finish_run(store, run, dict(stats))


def _fetch_one(store: Store, lead: DocumentLead, client: httpx.Client, doc_dir: Path) -> tuple[AcquisitionStatus, str]:
    try:
        ok = allowed(lead.url, USER_AGENT, client)
    except httpx.ProxyError as e:
        return AcquisitionStatus.BLOCKED_EGRESS, f"robots probe blocked by proxy: {e}"
    if ok is False:
        return AcquisitionStatus.ROBOTS_DISALLOWED, "robots.txt disallows this path"
    url = lead.url
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]  # scheme upgrade only; never an auth/robots/paywall workaround
    try:
        r = client.get(url)
    except httpx.ProxyError as e:
        return AcquisitionStatus.BLOCKED_EGRESS, f"egress proxy denied: {e}"
    except httpx.HTTPError as e:
        msg = str(e)
        if "403" in msg and "CONNECT" in msg:
            return AcquisitionStatus.BLOCKED_EGRESS, msg
        return AcquisitionStatus.NETWORK_ERROR, msg[:200]
    if r.status_code in (401, 403, 407):
        return AcquisitionStatus.HTTP_ERROR, f"HTTP {r.status_code} (not retried; no circumvention)"
    if r.status_code >= 400:
        return AcquisitionStatus.HTTP_ERROR, f"HTTP {r.status_code}"
    ct = r.headers.get("content-type", "")
    base = ct.split(";")[0].strip().lower()
    if base not in ("application/pdf", "text/html", "application/xhtml+xml", "text/plain"):
        return AcquisitionStatus.UNSUPPORTED_CONTENT, f"content-type {base or 'unknown'}"
    if "html" in base and any(marker in r.text.lower() for marker in (
        "an issue occurred while submitting your request", "verify you are human", "checking your browser",
        "<title>access denied", "<title>just a moment", "<title>403", "<title>502",
    )):
        return AcquisitionStatus.HTTP_ERROR, "HTTP 200 error/challenge document; not protocol evidence"
    register_document(store, lead, r.content, base, doc_dir=doc_dir)
    return AcquisitionStatus.FETCHED, "ok"
