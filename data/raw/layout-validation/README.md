# Layout validation documents

This directory holds the four real documents used to validate layout-aware extraction.
**The documents are not committed.** They are third-party works; only their identity lives in
this repository, in `MANIFEST.json`.

In the environment where this sprint ran, all four hosts were refused by the organisation's
egress policy (HTTP 403 at CONNECT), so none was retrieved and none was substituted.

## Populating the directory

From a network where these hosts are reachable:

```bash
uv run python scripts/fetch_layout_validation.py          # downloads and verifies hashes
uv run python scripts/run_layout_validation.py            # parses them and writes metrics
```

`fetch_layout_validation.py` refuses any file whose SHA-256 does not match
`expected_sha256`. A document whose identity cannot be established must not be used, however
closely its filename matches.
