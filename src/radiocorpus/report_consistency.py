"""Deterministic reports from normalized values, and executable summary claims."""

import json
from pathlib import Path


def identity_report(agencies):
    rows = sorted(agencies, key=lambda a: (a["state"] or "", a["canonical_name"]))
    count = sum(bool(a["official_website"]) for a in rows)
    lines = [
        "# Canary identity report",
        "",
        f"Agencies: {len(rows)}. Verified website assignments: {count}.",
        "",
        "Search-only assignments have been quarantined pending entity evidence. See the hardening audit for retrieval results.",
        "",
        "| State | Agency | Official website |",
        "|---|---|---|",
    ]
    lines += [f"| {a['state']} | {a['canonical_name']} | {a['official_website'] or 'UNKNOWN'} |" for a in rows]
    return "\n".join(lines) + "\n"


def check_claims(agencies, claims):
    indexed = {a["agency_id"]: a for a in agencies}
    errors = []
    for claim in claims:
        actual = indexed.get(claim["agency_id"], {}).get(claim["field"])
        if claim["agency_id"] not in indexed or actual != claim["expected"]:
            errors.append(f"{claim['agency_id']} {claim['field']}: report {claim['expected']!r}, data {actual!r}")
    return errors


def check_report(root):
    root = Path(root)
    data = root / "data/normalized/agencies.jsonl"
    if not data.exists():
        return ["normalized agency export missing"]
    agencies = [json.loads(line) for line in data.read_text().splitlines()]
    claims = json.loads((root / "data/audit/report_claims.json").read_text())
    errors = check_claims(agencies, claims)
    if (root / "docs/canary-report.md").read_text() != identity_report(agencies):
        errors.append("generated canary report differs from normalized data")
    return errors


def check_audit_metrics(root):
    # Script has no acquisition side effects; generation is pure over committed records.
    import importlib.util

    root = Path(root)
    spec = importlib.util.spec_from_file_location("audit_metrics", root / "scripts/build_audit_metrics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        metrics, report = module.generate()
    except AssertionError as error:
        return [str(error)]
    errors = []
    if json.loads((root / "data/audit/metrics.json").read_text()) != metrics:
        errors.append("stored audit metrics differ from evidence records")
    if (root / "docs/real-source-metrics.md").read_text() != report:
        errors.append("source report differs from evidence records")
    return errors
