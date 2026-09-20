"""Synthetic fixture loader. Fixture agencies use state ZZ and is_fixture=True so they can
never be confused with real agencies. Fixture documents are declared in
data/fixtures/manifest.json with the source_type and dates they are meant to simulate."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from radiocorpus import ids
from radiocorpus.acquisition.fetch import register_document
from radiocorpus.models import Agency, DocumentLead
from radiocorpus.models.common import AgencyType, LeadClass, ResearchStatus, SourceType, utcnow
from radiocorpus.store import Store


def load_fixtures(store: Store, fixtures_dir: Path, doc_dir: Path) -> dict[str, int]:
    manifest = json.loads((fixtures_dir / "manifest.json").read_text())
    n_ag = n_doc = 0
    with store.tx():
        for ag in manifest["agencies"]:
            aid = ids.agency_id("FIXTURE", ag["fixture_id"])
            if store.get_agency(aid) is None:
                store.upsert_agency(
                    Agency(
                        agency_id=aid,
                        canonical_name=ag["name"],
                        agency_type=AgencyType(ag["agency_type"]),
                        state="ZZ",
                        is_fixture=True,
                        research_status=ResearchStatus.DOCUMENTS_ACQUIRED,
                        source_registry_ids={"FIXTURE": [ag["fixture_id"]]},
                        parent_agency=ids.agency_id("FIXTURE", ag["parent_fixture_id"]) if ag.get("parent_fixture_id") else None,
                        dispatch_provider=ids.agency_id("FIXTURE", ag["dispatch_fixture_id"]) if ag.get("dispatch_fixture_id") else None,
                        notes="synthetic fixture; not a real agency",
                    )
                )
                n_ag += 1
        for d in manifest["documents"]:
            aid = ids.agency_id("FIXTURE", d["agency_fixture_id"])
            data = (fixtures_dir / d["file"]).read_bytes()
            url = d["url"]
            lead = DocumentLead(
                lead_id=ids.lead_id(aid, url, "fixture"),
                agency_id=aid,
                url=url,
                host=url.split("/")[2],
                title=d.get("title"),
                discovered_via="fixture",
                retrieved_at=utcnow(),
                lead_class=LeadClass.OFFICIAL_RADIO_POLICY_CANDIDATE,
                host_is_official=d.get("official_host", True),
            )
            store.upsert_lead(lead)
            src = register_document(
                store,
                lead,
                data,
                d["content_type"],
                doc_dir=doc_dir,
                source_type=SourceType(d["source_type"]),
                is_fixture=True,
                title=d.get("title"),
                issuing_authority=d.get("issuing_authority"),
            )
            for field in ("effective_date", "publication_date"):
                if d.get(field):
                    store.update_source_status(src.source_id, field=field, new_value=date.fromisoformat(d[field]), reason="fixture manifest")
            n_doc += 1
    return {"fixture_agencies": n_ag, "fixture_documents": n_doc, "at": datetime.now().isoformat()}
