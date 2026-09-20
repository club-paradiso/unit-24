"""Quarantine legacy website assertions and recompute fixture policy; retain source facts."""

import json
from pathlib import Path

from radiocorpus.conflicts.detect import detect_conflicts
from radiocorpus.eligibility.policy import assign_all
from radiocorpus.export import export_all
from radiocorpus.models import Agency, ProtocolFact, Source
from radiocorpus.provenance.classify import classify_all
from radiocorpus.report_consistency import identity_report
from radiocorpus.store import Store

ROOT = Path(__file__).resolve().parents[1]


def migrate():
    path = ROOT / "data/normalized/agencies.jsonl"
    agencies = [json.loads(line) for line in path.read_text().splitlines()]
    quarantine = ROOT / "data/audit/website_quarantine.jsonl"
    old = quarantine.read_text() if quarantine.exists() else ""
    for agency in agencies:
        if agency["official_website"] and not agency.get("identity_evidence"):
            old += (
                json.dumps(
                    {
                        "agency_id": agency["agency_id"],
                        "canonical_name": agency["canonical_name"],
                        "previous_website": agency["official_website"],
                        "previous_note": agency["notes"],
                        "reason": "legacy search-result assignment lacks entity proof",
                    }
                )
                + "\n"
            )
            agency["official_website"] = None
            agency["last_verified"] = None
            agency["notes"] = "Legacy search-only website quarantined; original basis preserved in data/audit/website_quarantine.jsonl"
    quarantine.write_text(old)
    path.write_text("".join(json.dumps(a, sort_keys=True) + "\n" for a in agencies))
    claims = [{"agency_id": a["agency_id"], "field": "official_website", "expected": a["official_website"]} for a in agencies]
    (ROOT / "data/audit/report_claims.json").write_text(json.dumps(claims, indent=2) + "\n")
    (ROOT / "docs/canary-report.md").write_text(identity_report(agencies))
    # Keep legacy evidence, but never export old auto-verified assertions as verified.
    directory = ROOT / "data/normalized/fixtures"
    store = Store()
    for file, model, insert in [
        ("agencies.jsonl", Agency, store.upsert_agency),
        ("sources.jsonl", Source, store.insert_source),
        ("facts_verified.jsonl", ProtocolFact, store.insert_fact),
        ("facts_unverified.jsonl", ProtocolFact, store.insert_fact),
    ]:
        for line in (directory / file).read_text().splitlines():
            insert(model.model_validate_json(line))
    classify_all(store)
    detect_conflicts(store)
    assign_all(store)
    export_all(store, directory, include_fixtures=True)


if __name__ == "__main__":
    migrate()
