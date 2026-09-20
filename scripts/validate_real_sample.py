"""Bounded acquisition harness. No nationwide discovery; no evidence auto-promotion."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from radiocorpus.acquisition.fetch import USER_AGENT, _fetch_one
from radiocorpus.extraction.codes import parse_code_blocks
from radiocorpus.extraction.phonetics import parse_phonetic_blocks
from radiocorpus.extraction.procedures import parse_procedure_blocks
from radiocorpus.extraction.text import blocks_for
from radiocorpus.models import Agency, DocumentLead
from radiocorpus.models.common import LeadClass, utcnow
from radiocorpus.store import Store

OUT = Path("data/audit/retrieval")


def inspect(row):
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / (row["canary_id"] + ".json")
    if output.exists():
        return json.loads(output.read_text())
    store = Store()
    store.upsert_agency(Agency(agency_id=row["canary_id"], canonical_name=row["name"], state=row["state"]))
    lead = DocumentLead(
        lead_id=row["canary_id"],
        agency_id=row["canary_id"],
        url=row["url"],
        host=row["url"].split("/")[2],
        discovered_via="bounded_audit",
        retrieved_at=utcnow(),
        lead_class=LeadClass.OFFICIAL_DOCUMENT_CANDIDATE,
    )
    store.upsert_lead(lead)
    # Preserve prior actual retrievals and failures; no retry against access controls.
    prior = {"CAN-S05": "CHP", "CAN-S12": "ID", "CAN-S14": "IN"}
    if row["canary_id"] in prior:
        probe = json.loads(Path(f"data/audit/probe-{prior[row['canary_id']]}.json").read_text())
        status, note, sources = probe["status"], probe["note"], probe["sources"]
    elif row["canary_id"] == "CAN-S09":
        status, note, sources = "http_error", "HTTP 403 observed in initial direct probe; not retried", []
    else:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=25) as client:
            status, note = _fetch_one(store, lead, client, Path("data/raw/documents"))
        sources = [s.model_dump(mode="json") for s in store.sources()]
    result = {**row, "retrieved_at": utcnow().isoformat(), "status": str(status), "note": note, "sources": sources}
    for source in sources:
        try:
            blocks = blocks_for(Path(source["local_path"]).read_bytes(), source["content_type"])
            result.update(
                block_count=len(blocks),
                page_count=len(blocks) if "pdf" in source["content_type"] else None,
                text_characters=sum(len(b.text) for b in blocks),
                negligible_text_blocks=sum(len(b.text.strip()) < 20 for b in blocks),
                code_candidates=len(parse_code_blocks(blocks)),
                phonetic_candidates=len(parse_phonetic_blocks(blocks)),
                procedure_candidates=len(parse_procedure_blocks(blocks)),
            )
            text_dir = Path("data/raw/audit-text")
            text_dir.mkdir(parents=True, exist_ok=True)
            (text_dir / (row["canary_id"] + ".txt")).write_text("\n\n".join(b.locator + "\n" + b.text for b in blocks))
        except Exception as error:
            result["parser_failure"] = str(error)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    rows = json.loads(Path("data/audit/sample_plan.json").read_text())
    with ThreadPoolExecutor(max_workers=5) as executor:
        for result in executor.map(inspect, rows):
            print(result["canary_id"], result["status"], result.get("text_characters"), result.get("parser_failure"), flush=True)
