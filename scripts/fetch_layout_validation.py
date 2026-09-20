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
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "raw" / "layout-validation"
USER_AGENT = "radiocorpus-research/0.1 (+public-safety radio protocol corpus)"


def main() -> int:
    manifest = json.loads((DIR / "MANIFEST.json").read_text())
    failures: list[str] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60, trust_env=True) as client:
        for doc in manifest["documents"]:
            target = DIR / doc["filename"]
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == doc["expected_sha256"]:
                print(f"ok (cached)   {doc['key']}")
                continue
            try:
                response = client.get(doc["canonical_url"])
                response.raise_for_status()
            except httpx.HTTPError as error:
                failures.append(f"{doc['key']}: {error}")
                print(f"FAILED        {doc['key']}: {error}")
                continue
            digest = hashlib.sha256(response.content).hexdigest()
            if digest != doc["expected_sha256"]:
                failures.append(f"{doc['key']}: hash mismatch (got {digest})")
                print(f"HASH MISMATCH {doc['key']}: expected {doc['expected_sha256']}, got {digest}")
                print("              The document at this URL is not the one that was audited. Not saving it.")
                continue
            target.write_bytes(response.content)
            print(f"ok            {doc['key']} -> {target.name} ({len(response.content)} bytes)")
    if failures:
        print(f"\n{len(failures)} document(s) unavailable or unverified; layout validation cannot use them.")
        return 1
    print("\nAll four documents verified. Next: uv run python scripts/run_layout_validation.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
