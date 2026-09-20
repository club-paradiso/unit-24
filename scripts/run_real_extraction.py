"""Reproduce extraction against previously acquired bytes without network access."""

import json
from pathlib import Path

from radiocorpus.conflicts.detect import detect_conflicts
from radiocorpus.eligibility.policy import assign_all
from radiocorpus.extraction.stage import extract_all
from radiocorpus.extraction.text import blocks_for
from radiocorpus.models import Agency, DocumentRecord, Source
from radiocorpus.provenance.classify import classify_all
from radiocorpus.store import Store
from radiocorpus.validation.rules import validate_all


def run():
    db = Path("data/intermediate/real-audit.sqlite")
    db.parent.mkdir(parents=True, exist_ok=True)
    store = Store(db)
    for path in sorted(Path("data/audit/retrieval").glob("*.json")):
        row = json.loads(path.read_text())
        aid = row["canary_id"]
        store.upsert_agency(Agency(agency_id=aid, canonical_name=row["name"], state=row["state"]))
        for value in row["sources"]:
            # The sample target is an attribution candidate, not proven issuing authority.
            value.update(agency_or_jurisdiction=aid, title=value["title"] or row["name"] + " - audit candidate")
            source = Source.model_validate(value)
            store.insert_source(source)
            local = Path(source.local_path)
            store.insert_document(
                DocumentRecord(
                    source_id=source.source_id,
                    document_hash=source.document_hash,
                    local_path=source.local_path,
                    content_type=source.content_type,
                    byte_length=local.stat().st_size,
                )
            )
            try:
                blocks = blocks_for(local.read_bytes(), source.content_type)
                row["after_html_fix"] = dict(block_count=len(blocks), text_characters=sum(len(b.text) for b in blocks))
            except Exception as error:
                row["after_html_fix"] = {"parser_failure": str(error)}
        path.write_text(json.dumps(row, indent=2) + "\n")
    result = extract_all(store)
    classify_all(store)
    validate_all(store)
    detect_conflicts(store)
    assign_all(store)
    store.commit()
    Path("data/audit/real_facts.jsonl").write_text("".join(f.model_dump_json() + "\n" for f in store.facts()))
    Path("data/audit/real_eligibility.jsonl").write_text("".join(e.model_dump_json() + "\n" for e in store.eligibility("fact")))
    for name, values in [("real_sources", store.sources()), ("real_documents", store.documents()), ("real_conflicts", store.conflicts())]:
        Path(f"data/audit/{name}.jsonl").write_text("".join(value.model_dump_json() + "\n" for value in values))
    print(result.stats)
    return store


if __name__ == "__main__":
    run()
