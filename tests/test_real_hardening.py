import io
import json
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from radiocorpus.extraction.text import OCRRequired, html_blocks, pdf_blocks
from radiocorpus.models import RegistryRecord
from radiocorpus.report_consistency import check_claims, check_report

ROOT = Path(__file__).resolve().parents[1]


def test_malformed_pdf_is_not_text():
    with pytest.raises(PdfReadError):
        pdf_blocks(b"%PDF-broken")


def image_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(100, 100)
    image = DecodedStreamObject()
    image.set_data(b"\x00\x00\x00")
    image.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): writer._add_object(image)})})
    content = DecodedStreamObject()
    content.set_data(b"q 100 0 0 100 0 0 cm /Im0 Do Q")
    page[NameObject("/Contents")] = writer._add_object(content)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_scanned_pdf_is_explicitly_gated():
    with pytest.raises(OCRRequired, match="p.1"):
        pdf_blocks(image_pdf())


def test_ocr_interface_preserves_page_and_method():
    class SyntheticOCR:
        def extract_page(self, data, page):
            assert page == 1
            return "10-4 Acknowledged"

    blocks = pdf_blocks(image_pdf(), ocr=SyntheticOCR())
    assert blocks[0].locator == "p.1" and blocks[0].method == "ocr"


def test_native_pdf_does_not_call_ocr():
    class ForbiddenOCR:
        def extract_page(self, data, page):
            raise AssertionError("native text must not be OCRed")

    data = (ROOT / "data/fixtures/fx001_exampleville_general_order_2009.pdf").read_bytes()
    assert all(b.method == "native_pdf_text" for b in pdf_blocks(data, ocr=ForbiddenOCR()))


def test_html_leaf_paragraphs_and_table():
    blocks = html_blocks(b"<html><body><p>Use plain language.</p><table><tr><td>10-4</td><td>Acknowledged</td></tr></table></body></html>")
    assert any(b.text == "Use plain language." for b in blocks)
    assert any(b.locator == "html:table[1]>tr[1]" and b.text == "10-4 | Acknowledged" for b in blocks)


def test_report_detects_original_miami_contradiction():
    agency = {"agency_id": "miami", "official_website": "https://www.southmiamifl.gov/184/Police-Department"}
    assert check_claims([agency], [{"agency_id": "miami", "field": "official_website", "expected": None}])


def test_committed_report_matches_data():
    assert not check_report(ROOT)


def test_real_audit_locators_and_sources_are_referentially_intact():
    facts = {r["fact_id"]: r for r in map(json.loads, (ROOT / "data/audit/real_facts.jsonl").read_text().splitlines())}
    audits = list(map(json.loads, (ROOT / "data/audit/fact_audit.jsonl").read_text().splitlines()))
    assert len(audits) >= 100
    for audit in audits:
        fact = facts[audit["fact_id"]]
        assert fact["locator"] == audit["locator"] and fact["source_id"] == audit["source_id"]
        assert not audit["safe_expected_answer"]


def test_changed_registry_snapshot_cannot_silently_disappear(store):
    record = RegistryRecord(registry="STATE_2026", external_id="1", name="Before Police", state="FL")
    store.upsert_registry_record(record)
    with pytest.raises(ValueError, match="snapshot collision"):
        store.upsert_registry_record(record.model_copy(update={"name": "After Sheriff"}))
    assert store.upsert_registry_record(record.model_copy(update={"registry": "STATE_2027", "name": "After Sheriff"}))
    assert store.registry_count() == 2


def test_playback_requires_acquired_untampered_bytes(store, tmp_path):
    from radiocorpus.eligibility.policy import assign_all
    from radiocorpus.ids import document_hash
    from radiocorpus.invariants import check_all
    from radiocorpus.models import Agency, DocumentRecord
    from radiocorpus.models.common import EligibilityState
    from tests.test_evidence_hardening import accepted_fact, confirmed, official

    store.upsert_agency(Agency(agency_id="agy_a", canonical_name="A Police Department", state="TX"))
    data = b"A Police Department, Texas. Active policy. 10-4 Ack"
    path = tmp_path / "evidence.txt"
    path.write_bytes(data)
    source = confirmed(official())
    source.document_hash = document_hash(data)
    store.insert_source(source)
    from radiocorpus.models.evidence import IssuingAuthorityEvidence

    source.issuing_authority_id = "agy_a"
    source.issuing_authority_evidence = IssuingAuthorityEvidence(
        evidence_source_id=source.source_id,
        target_source_id=source.source_id,
        issuing_authority_id="agy_a",
        locator="line.1",
        excerpt="A Police Department, Texas",
        verified_by="synthetic reviewer",
        verification_status="verified",
    )
    store.update_source_status(source.source_id, field="issuing_authority_id", new_value="agy_a", reason="test")
    store.update_source_status(
        source.source_id, field="issuing_authority_evidence", new_value=source.issuing_authority_evidence.model_dump(), reason="test"
    )
    store.insert_fact(accepted_fact(source))
    assign_all(store)
    assert store.eligibility("fact")[0].state == EligibilityState.RESEARCH_ONLY
    store.insert_document(
        DocumentRecord(
            source_id=source.source_id, document_hash=source.document_hash, local_path=str(path), content_type="text/plain", byte_length=len(data)
        )
    )
    assign_all(store)
    assert store.eligibility("fact")[0].state == EligibilityState.PLAYABLE_VERIFIED
    assert not any(check_all(store).values())
    path.write_bytes(b"tampered")
    assert any(check_all(store).values())
    assign_all(store)
    assert store.eligibility("fact")[0].state == EligibilityState.RESEARCH_ONLY

    path.write_bytes(data)
    # Appending a contradictory accepted fact must rebuild even an empty conflict table.
    contradictory = accepted_fact(source, fact_id="fct_2")
    contradictory.value.meaning = "Contradictory meaning"
    contradictory.review_evidence.value_fingerprint = contradictory.value_fingerprint()
    store.insert_fact(contradictory)
    assign_all(store)
    assert all(e.state == EligibilityState.CONFLICT_REQUIRES_REVIEW for e in store.eligibility("fact"))
    assert store.conflicts()


def test_mirror_sources_each_extract_and_malformed_document_isolated(store, tmp_path):
    from radiocorpus.acquisition.fetch import register_document
    from radiocorpus.extraction.stage import extract_all
    from radiocorpus.models import Agency, DocumentLead

    for index in range(3):
        agency_id = f"agency_{index}"
        store.upsert_agency(Agency(agency_id=agency_id, canonical_name=agency_id, state="TX"))
        lead = DocumentLead(
            lead_id=str(index),
            agency_id=agency_id,
            url=f"https://example.gov/{index}",
            host="example.gov",
            discovered_via="test",
            retrieved_at="2026-09-20T00:00:00Z",
        )
        # The readable document must satisfy the v3 structural contract (a run of sibling
        # records); a single code-shaped line no longer yields a fact, and the isolation
        # assertion below would then pass for the wrong reason.
        readable = b"10-4 Acknowledged\n10-8 In service\n10-97 Arrived on scene"
        register_document(
            store,
            lead,
            b"%PDF-broken" if index == 0 else readable,
            "application/pdf" if index == 0 else "text/plain",
            doc_dir=tmp_path,
        )
    run = extract_all(store)
    assert run.stats["parser_failures"] == 1
    assert run.stats["documents"] == 2
    assert {f.agency_id for f in store.facts()} == {"agency_1", "agency_2"}
    assert len(store.documents()) == 2
    assert all(f.text_extraction_method == "text" for f in store.facts())


def test_error_page_with_http_200_is_not_evidence(store, tmp_path):
    import httpx

    from radiocorpus.acquisition.fetch import _fetch_one
    from radiocorpus.models import DocumentLead

    def response(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html><title>Access denied</title></html>", request=request)

    lead = DocumentLead(
        lead_id="error", agency_id="a", url="https://example.gov/x", host="example.gov", discovered_via="test", retrieved_at="2026-09-20T00:00:00Z"
    )
    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        status, _ = _fetch_one(store, lead, client, tmp_path)
    assert status == "http_error"
    assert not store.sources()


def test_committed_snapshots_are_checked():
    from radiocorpus.snapshot_check import check_snapshot

    assert not check_snapshot(ROOT / "data/normalized")
    assert not check_snapshot(ROOT / "data/normalized/fixtures")


def test_verified_snapshot_cannot_omit_review_and_eligibility(tmp_path):
    from radiocorpus.snapshot_check import check_snapshot
    from tests.test_eligibility_invariants import _fact, _src

    fact = _fact(verification_status="verified")
    (tmp_path / "facts_verified.jsonl").write_text(fact.model_dump_json() + "\n")
    (tmp_path / "sources.jsonl").write_text(_src().model_dump_json() + "\n")
    assert check_snapshot(tmp_path)


def test_hosted_other_issuer_not_same_agency_applicability(store):
    from radiocorpus.provenance.evidence import applicability_matches
    from tests.test_eligibility_invariants import _fact
    from tests.test_evidence_hardening import official

    source = official()
    source.issuing_authority_id = "fbi"
    assert not applicability_matches(store, _fact(), source)
