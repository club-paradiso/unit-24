"""Check committed JSONL too: a fresh CI database must not create a vacuous pass."""

from radiocorpus.invariants import check_all
from radiocorpus.models import Agency, Conflict, DocumentRecord, EligibilityDecision, ProtocolFact, Source
from radiocorpus.store import Store


def check_snapshot(directory):
    store = Store()
    for filename, model, insert in [
        ("agencies.jsonl", Agency, store.upsert_agency),
        ("sources.jsonl", Source, store.insert_source),
        ("documents.jsonl", DocumentRecord, store.insert_document),
        ("facts_verified.jsonl", ProtocolFact, store.insert_fact),
        ("facts_unverified.jsonl", ProtocolFact, store.insert_fact),
        ("conflicts.jsonl", Conflict, store.upsert_conflict),
        ("eligibility.jsonl", EligibilityDecision, store.upsert_eligibility),
    ]:
        path = directory / filename
        if path.exists():
            for line in path.read_text().splitlines():
                insert(model.model_validate_json(line))
    return [f"{name}: {value}" for name, values in check_all(store).items() for value in values]
