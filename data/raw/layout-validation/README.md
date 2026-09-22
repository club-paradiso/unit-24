# Layout validation documents

This directory holds the three real documents used to validate layout-aware extraction.
**The documents are not committed.** They are third-party works; only their identity lives in
this repository, in `MANIFEST.json`.

Every host is refused by the organisation's egress policy (HTTP 403 at CONNECT), so on
2026-09-22 the files were downloaded outside the build environment and placed here by hand.
Nothing was substituted: each came from its `canonical_url`, and each matches its
`expected_sha256` and byte length exactly.

## The set is three, not four

It was four. The Chicago Police Department directive was removed on 2026-09-22 because its
source cannot supply a document matching `expected_sha256`, and no substitute may stand in for
it. `directives.chicagopolice.org/api/publicDirective/6607` builds the PDF per request rather
than serving a stored file: the footer of all eleven pages carries the download time to the
minute, and the trailer `/ID` and `CreationDate` are fresh each time, so four downloads
produced four different whole-file hashes. The audited copy from 2026-09-20 carried that
minute's stamp and no copy of those bytes survives anywhere in this repository or on the
machine, so its expected hash can never be reproduced.

The entry is kept in `MANIFEST.json` under `excluded_documents`, with the evidence a
re-admission would rest on, so the set cannot drift back to four without someone reading why
it became three. Nothing reads that key — the scripts iterate `documents`.

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
