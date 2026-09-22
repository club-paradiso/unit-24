"""Fetch the four layout-validation documents and verify their identity.

Blocked in the build environment: every host was refused by the organisation egress policy
(HTTP 403 at CONNECT). Run this from a network where the hosts are reachable.

A download whose SHA-256 does not match ``expected_sha256`` in MANIFEST.json is rejected and
deleted. A document whose identity cannot be established must not be used, however closely
its filename matches: silently substituting a similar document would invalidate every metric
computed from it.

    uv run python scripts/fetch_layout_validation.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "raw" / "layout-validation"
USER_AGENT = "radiocorpus-research/0.1 (+public-safety radio protocol corpus)"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(doc: dict, **fields) -> dict:
    """What was actually retrieved, kept separately from what was expected.

    The host that served a file and the authority that issued it are different facts, and the
    manifest's issuing authority is a claim from the source ledger, not something the bytes
    have yet been checked against. Conflating the two is how a mirror becomes an official
    source, so they are recorded as separate fields and the issuer stays unverified until a
    reviewer confirms it from the document itself.
    """
    return {
        "key": doc["key"],
        "canonical_url": doc["canonical_url"],
        "expected_sha256": doc["expected_sha256"],
        "host": urlparse(doc["canonical_url"]).hostname,
        "issuing_authority_claimed": doc.get("issuing_authority_claimed") or doc.get("agency"),
        "issuing_authority_verified": None,
        "issuer_verification_note": "requires reading the document; not established by retrieval",
        "attempted_at": _now(),
        **fields,
    }


def main() -> int:
    manifest = json.loads((DIR / "MANIFEST.json").read_text())
    failures: list[str] = []
    records: list[dict] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60, trust_env=True) as client:
        for doc in manifest["documents"]:
            target = DIR / doc["filename"]
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == doc["expected_sha256"]:
                print(f"ok (cached)   {doc['key']}")
                records.append(_record(doc, status="CACHED", sha256=doc["expected_sha256"]))
                continue
            try:
                response = client.get(doc["canonical_url"])
                response.raise_for_status()
            except httpx.HTTPError as error:
                failures.append(f"{doc['key']}: {error}")
                print(f"FAILED        {doc['key']}: {error}")
                records.append(_record(doc, status="UNAVAILABLE", error=str(error)))
                continue

            final_host = urlparse(str(response.url)).hostname
            expected_host = urlparse(doc["canonical_url"]).hostname
            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            # A 200 is not provenance. A redirect onto another host, or an HTML page where a
            # PDF was expected, means something other than the audited document answered —
            # a search page, a portal, a mirror. None of those is authoritative here.
            if final_host != expected_host:
                failures.append(f"{doc['key']}: redirected to {final_host}")
                print(f"REDIRECTED    {doc['key']}: {expected_host} -> {final_host}; refusing, this is not the "
                      "documented host and a mirror is not an authoritative source")
                records.append(_record(doc, status="REDIRECTED_OFF_HOST", final_host=final_host))
                continue
            if content_type and content_type != "application/pdf":
                failures.append(f"{doc['key']}: content-type {content_type}")
                print(f"WRONG TYPE    {doc['key']}: served {content_type}, expected application/pdf; not saving")
                records.append(_record(doc, status="WRONG_CONTENT_TYPE", content_type=content_type))
                continue

            digest = hashlib.sha256(response.content).hexdigest()
            if digest != doc["expected_sha256"]:
                failures.append(f"{doc['key']}: hash mismatch (got {digest})")
                print(f"HASH MISMATCH {doc['key']}: expected {doc['expected_sha256']}, got {digest}")
                print("              The document at this URL is not the one that was audited. Not saving it.")
                records.append(_record(doc, status="HASH_MISMATCH", sha256=digest, byte_length=len(response.content)))
                continue
            target.write_bytes(response.content)
            print(f"ok            {doc['key']} -> {target.name} ({len(response.content)} bytes)")
            records.append(
                _record(
                    doc,
                    status="VERIFIED",
                    sha256=digest,
                    byte_length=len(response.content),
                    content_type=content_type,
                    final_url=str(response.url),
                    retrieved_at=_now(),
                    local_path=str(target.relative_to(ROOT)),
                )
            )
    (DIR / "retrieval_log.json").write_text(
        json.dumps({"attempted_at": _now(), "documents": records}, indent=2, sort_keys=True) + "\n"
    )
    if failures:
        print(f"\n{len(failures)} document(s) unavailable or unverified; layout validation cannot use them.")
        print(f"Per-document detail written to {(DIR / 'retrieval_log.json').relative_to(ROOT)}")
        return 1
    print("\nAll four documents verified. Next: uv run python scripts/run_layout_validation.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
