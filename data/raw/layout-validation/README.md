# Layout validation documents

This directory holds the four real documents used to validate layout-aware extraction.
**The documents are not committed.** They are third-party works; only their identity lives in
this repository, in `MANIFEST.json`.

On 2026-09-22 every host was refused by the organisation's egress policy (HTTP 403 at
CONNECT), so the three original files were downloaded outside the build environment and placed
here by hand. On 2026-10-12 the hosts were reachable from the build environment:
`fetch_layout_validation.py` re-downloaded the California and Indiana documents and both matched
`expected_sha256` exactly. The Philadelphia directive's origin answered the script with HTTP
403 (the connection itself was allowed), so on 2026-10-13 it was downloaded by hand in a browser
from its `canonical_url` and placed here; it matches its `expected_sha256` and byte length
exactly. Nothing was substituted for any document.

## The set is four again — with a different fourth document

The Chicago directive below was the set's only single-column directive with nested lettered and
numbered clauses. That case is now covered by **Florida Highway Patrol Policy 14.01,
COMMUNICATIONS** (`FL_FHP_POLICY_14_01`, revised 2024-06-18, 42 pages): a single-column policy
whose rules nest four levels deep (`A.` → `1.` → `a.` → `1)`) under numbered sections, covering
radio, telephone and CAD procedures for the regional communications centers.

**Its identity is weaker than the other three's.** It came from the repository's own discovery
output (`lead_58e822da138cdbb6`), had never been fetched, and has no source-ledger record, so its
`source_id` is `null`. Its `expected_sha256` is the hash of the bytes received on first
acquisition (2026-10-12), not a hash a previous sprint audited. The PDF's embedded metadata
claims the subject "Identification Cards"; the body is the communications policy, and the body
is what was checked.

## Why Chicago was removed

The set was briefly three. The Chicago Police Department directive was removed on 2026-09-22
because its source cannot supply a document matching `expected_sha256`, and no substitute may stand in for
it. `directives.chicagopolice.org/api/publicDirective/6607` builds the PDF per request rather
than serving a stored file: the footer of all eleven pages carries the download time to the
minute, and the trailer `/ID` and `CreationDate` are fresh each time, so four downloads
produced four different whole-file hashes. The audited copy from 2026-09-20 carried that
minute's stamp and no copy of those bytes survives anywhere in this repository or on the
machine, so its expected hash can never be reproduced.

The entry is kept in `MANIFEST.json` under `excluded_documents`, with the evidence a
re-admission would rest on, so Chicago cannot be silently restored without someone reading why
it was removed. Nothing reads that key — the scripts iterate `documents`.

**The removal is scoped to layout validation.** `CHI_CPD_DIRECTIVE` stays in `DOCUMENT_KEYS`
and in the audit, replay, coverage and adjudication artifacts: those record what a previous
sprint measured when the document was retrievable, and no historical figure changes here.

Re-admitting it means deciding what identity means for a source that generates its bytes per
request. It does not mean editing `expected_sha256` to match whatever arrived.

## Populating the directory

From a network where these hosts are reachable:

```bash
uv run python scripts/fetch_layout_validation.py          # downloads and verifies hashes
uv run python scripts/run_layout_validation.py            # parses them and writes metrics
```

`fetch_layout_validation.py` refuses any file whose SHA-256 does not match
`expected_sha256`. A document whose identity cannot be established must not be used, however
closely its filename matches.
