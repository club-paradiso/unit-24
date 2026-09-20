import json
from datetime import date

import pytest
from pydantic import ValidationError

from radiocorpus.models import Agency, CodeMeaning, PhoneticLetter, ProtocolFact, Source
from radiocorpus.models.common import ExtractionMethod, FactType, ReviewStatus, SourceQuality, SourceType, VerificationStatus


def _fact(**kw):
    base = dict(
        fact_id="fct_x",
        agency_id="agy_a",
        fact_type=FactType.CODE_MEANING,
        key="10-4",
        value=CodeMeaning(code_system="TEN_CODE", code="10-4", meaning="Acknowledged"),
        source_id="src_1",
        locator="p.1",
        excerpt="10-4 Acknowledged",
        confidence=0.9,
        extraction_method=ExtractionMethod.DETERMINISTIC_PARSER,
    )
    base.update(kw)
    return ProtocolFact(**base)


def test_fixture_state_reserved():
    with pytest.raises(ValidationError):
        Agency(agency_id="agy_1", canonical_name="X", state="ZZ")
    Agency(agency_id="agy_1", canonical_name="X", state="ZZ", is_fixture=True)


def test_unknown_state_rejected():
    with pytest.raises(ValidationError):
        Agency(agency_id="agy_1", canonical_name="X", state="QQ")


def test_agency_validity_dates():
    with pytest.raises(ValidationError):
        Agency(agency_id="a", canonical_name="X", valid_from=date(2020, 1, 1), valid_to=date(2019, 1, 1))


def test_fact_requires_source_and_locator():
    with pytest.raises(ValidationError):
        _fact(source_id="")
    with pytest.raises(ValidationError):
        _fact(locator="")


def test_fact_type_must_match_value_kind():
    with pytest.raises(ValidationError):
        _fact(fact_type=FactType.PHONETIC_LETTER)


def test_excerpt_limit_prevents_document_mirroring():
    with pytest.raises(ValidationError):
        _fact(excerpt="x" * 401)


def test_model_output_cannot_be_verified_without_human():
    with pytest.raises(ValidationError):
        _fact(extraction_method=ExtractionMethod.MODEL, extraction_model="m", verification_status=VerificationStatus.VERIFIED)
    with pytest.raises(ValidationError):
        _fact(extraction_method=ExtractionMethod.MODEL)  # model id required
    _fact(
        extraction_method=ExtractionMethod.MODEL,
        extraction_model="m",
        verification_status=VerificationStatus.VERIFIED,
        review_status=ReviewStatus.HUMAN_ACCEPTED,
    )


def test_effective_dates_ordered():
    with pytest.raises(ValidationError):
        _fact(effective_from=date(2020, 1, 1), effective_to=date(2019, 1, 1))


def test_phonetic_letter_validation():
    with pytest.raises(ValidationError):
        PhoneticLetter(letter="AB", word="Adam", system="LOCAL")
    assert PhoneticLetter(letter="a", word="Adam", system="LOCAL").letter == "A"


def test_official_source_requires_hash():
    with pytest.raises(ValidationError):
        Source(
            source_id="s",
            source_type=SourceType.AGENCY_POLICY_MANUAL,
            title=None,
            issuing_authority=None,
            agency_or_jurisdiction=None,
            canonical_url="https://x.gov/a.pdf",
            source_quality=SourceQuality.OFFICIAL_CURRENT,
        )


def test_crowdsourced_never_official():
    with pytest.raises(ValidationError):
        Source(
            source_id="s",
            source_type=SourceType.ENTHUSIAST_OR_CROWDSOURCED,
            title=None,
            issuing_authority=None,
            agency_or_jurisdiction=None,
            canonical_url="https://x.net",
            document_hash="sha256:aa",
            source_quality=SourceQuality.OFFICIAL_CURRENT,
        )


def test_search_result_always_unverified():
    with pytest.raises(ValidationError):
        Source(
            source_id="s",
            source_type=SourceType.SEARCH_ENGINE_RESULT,
            title=None,
            issuing_authority=None,
            agency_or_jurisdiction=None,
            canonical_url="https://x.gov",
            source_quality=SourceQuality.SECONDARY_CORROBORATED,
        )


def test_json_schema_export_roundtrip():
    schema = ProtocolFact.model_json_schema()
    assert "value" in schema["properties"]
    json.dumps(schema)
