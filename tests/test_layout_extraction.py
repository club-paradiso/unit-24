"""Regression tests for layout-aware extraction.

Each test names the real failure it guards against. The failures were found by an
independent review of four real documents; the fixtures here reproduce the *geometry* of
those failures with invented wording, so the regression is real but no third-party document
is reproduced in the repository.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from radiocorpus.evaluation.gold import Label, build_gold, classify_failure, derive_label
from radiocorpus.evaluation.metrics import summarise
from radiocorpus.evaluation.replay import replay
from radiocorpus.extraction.codes import parse_code_blocks, parse_codes
from radiocorpus.extraction.context import governed_by_comm_verb, numeric_token_is_date
from radiocorpus.extraction.phonetics import describe_alphabet, parse_phonetic_blocks, parse_phonetics
from radiocorpus.extraction.procedures import parse_procedure_blocks, parse_procedures, split_sentences
from radiocorpus.extraction.text import TextBlock
from radiocorpus.layout import cache as layout_cache
from radiocorpus.layout.backends import layout_for
from radiocorpus.layout.model import LAYOUT_VERSION, BlockType, layout_code_fingerprint

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_FIXTURES = ROOT / "data" / "fixtures" / "layout"
AUDIT = ROOT / "data" / "audit"


def layout(name: str):
    return layout_for((LAYOUT_FIXTURES / name).read_bytes(), "application/pdf")


# ---------------------------------------------------------------- known failure A: dates


def test_revision_date_is_not_an_eleven_code():
    """Philadelphia: the revision date 09-11-18 was emitted as eleven-code 11-18."""
    codes = parse_codes(layout("lx02_revision_date_table.pdf"))
    assert codes == []


def test_revision_date_rejected_on_the_exact_audited_line():
    line = "*3      0172   09-11-18  Changes"
    assert [c.code for c in parse_code_blocks([TextBlock("p.16", line)])] == []


@pytest.mark.parametrize(
    "line",
    [
        "Issued Date: 03-08-13 Effective Date: 03-08-13",
        "Revised 12-05-19 by the Commissioner",
        "Rev. 10-2019 Policy",
        "Contact the desk at 215-686-3000",
    ],
)
def test_date_and_phone_shapes_never_yield_codes(line):
    assert parse_code_blocks([TextBlock("p.1", line)]) == []


def test_date_detection_is_positional_not_literal():
    """The rule is a boundary rule, so it generalises beyond any one date."""
    text = "07-22-91"
    assert numeric_token_is_date(text, 3, 8)  # the "22-91" fragment sits inside a date
    plain = "10-4 Acknowledged"
    assert not numeric_token_is_date(plain, 0, 4)


# ---------------------------------------------------------------- known failure B: headings


def test_enumerated_heading_is_not_a_phonetic_pair():
    """Philadelphia 'C. COMMUNICATIONS' and Indiana 'A. Attempt' became phonetic mappings."""
    assert parse_phonetics(layout("lx03_enumerated_headings.pdf")) == []


@pytest.mark.parametrize(
    "line",
    [
        "*5  C. COMMUNICATIONS FAILURE:",
        "A. Attempt to Locate (ATL) messages are for non-criminal activity; example, missing person,",
        "B. Broadcasts relative to district-wide need-to-know and timely information shall be transmitted",
    ],
)
def test_audited_heading_lines_yield_no_phonetics(line):
    assert parse_phonetic_blocks([TextBlock("p.1", line)]) == []


def test_isolated_pair_without_alphabet_context_is_refused():
    """A single LETTER+WORD resemblance is never enough."""
    assert parse_phonetic_blocks([TextBlock("p.1", "B Adam\nQ Section\nA Alpha")]) == []


# ---------------------------------------------------------------- known failure F: columns


def test_multi_column_table_does_not_bleed_between_columns():
    """CHP: a wrapped cell in column 2 was read as part of column 1's code meaning."""
    codes = {c.code: c.meaning for c in parse_codes(layout("lx01_multicolumn_code_table.pdf"))}
    assert codes["10-4"] == "Message received"  # not "Message received armed"
    assert codes["10-36A"] == "Confidential information subject possibly armed"


def test_wrapped_cell_is_reattached_to_its_own_record():
    cands = {c.code: c for c in parse_codes(layout("lx01_multicolumn_code_table.pdf"))}
    assert cands["10-36A"].continuation_lines == 1
    assert any("continuation" in e for e in cands["10-36A"].evidence)


def test_statutory_column_is_not_read_as_codes():
    codes = {c.code for c in parse_codes(layout("lx01_multicolumn_code_table.pdf"))}
    assert not any(c.startswith(("23152", "23153", "187", "211")) for c in codes)


def test_column_reading_order_is_column_major():
    """Never join the foot of one column to the head of the next."""
    doc = layout("lx01_multicolumn_code_table.pdf")
    blocks = [b for b in doc.included_blocks() if b.column_id is not None]
    columns = [b.column_id for b in blocks]
    assert columns == sorted(columns), "blocks must be grouped by column, not interleaved by row"


def test_single_column_document_is_not_split():
    doc = layout("lx09_single_column_narrative.pdf")
    assert max(p.column_count for p in doc.pages) == 1
    assert any("single_column" in note for note in doc.pages[0].notes)


# ---------------------------------------------------------------- page furniture


def test_repeated_footer_with_code_token_is_suppressed():
    doc = layout("lx05_footer_code_token.pdf")
    excluded = [b for p in doc.pages for b in p.blocks if b.excluded]
    assert excluded, "a footer repeated on every page must be marked"
    assert all(b.exclusion_reason for b in excluded)
    assert parse_codes(doc) == [], "a code-shaped token in page furniture is not a code"


def test_repeated_header_is_suppressed_but_body_survives():
    doc = layout("lx08_repeated_header.pdf")
    excluded = [b for p in doc.pages for b in p.blocks if b.excluded]
    assert any("header" in (b.exclusion_reason or "") for b in excluded)
    assert any("advise the dispatcher" in b.text for b in doc.included_blocks())
    assert [c.procedure for c in parse_procedures(doc)] == ["location_address"]


def test_suppressed_furniture_is_retained_for_audit():
    """Excluded material is marked, never deleted."""
    doc = layout("lx05_footer_code_token.pdf")
    assert any(b.excluded for b in doc.blocks)
    assert len(doc.blocks) > len(doc.included_blocks())


# ---------------------------------------------------------------- page boundaries


def test_rule_carries_context_across_a_page_break():
    """Philadelphia: a rule lost the broadcast format that continued on the next page."""
    procs = parse_procedures(layout("lx06_page_boundary_rule.pdf"))
    assert len(procs) == 1
    rule = procs[0]
    assert rule.crosses_page is True
    assert "need not repeat" in (rule.context_after or "")


def test_wrapped_sentence_is_reassembled_before_splitting():
    doc = layout("lx06_page_boundary_rule.pdf")
    assert any("until the dispatcher acknowledges" in b.text for b in doc.included_blocks())


# ---------------------------------------------------------------- phonetic system labels


def test_local_alphabet_divergence_is_preserved_not_normalised():
    """A label is descriptive metadata; it must never rewrite a local mapping."""
    report = describe_alphabet(parse_phonetics(layout("lx04_local_alphabet_divergence.pdf")))
    assert len(report.mappings) == 26
    assert report.mappings["Z"] == "ZULU"  # APCO reference says ZEBRA; the local word stands
    assert report.divergences["Z"] == {"local": "ZULU", "reference": "ZEBRA"}
    assert any("local_divergences_preserved" in e for e in report.evidence)


def test_label_requires_enough_letters():
    cands = parse_phonetic_blocks([TextBlock("p.1", "A Adam\nB Boy\nC Charles\nD David\nE Edward")])
    report = describe_alphabet(cands)
    assert report.label == "UNKNOWN"
    assert len(report.mappings) == 5


# ---------------------------------------------------------------- semantic gating


def test_document_copy_is_not_radio_acknowledgement():
    """Chicago and Philadelphia: 'copy' as a noun produced acknowledgement candidates."""
    assert parse_procedures(layout("lx07_non_radio_copy_and_plate.pdf")) == []


@pytest.mark.parametrize(
    "line",
    [
        "NOTE: A copy will be retained in the unit files in accordance with existing records-retention requirements.",
        "The copy will be made available to you by Police Radio upon receipt of a memorandum approved by your Commanding Officer.",
        "Department members must have a license plate impounded with the vehicle before the tow operator removes it.",
        "The greeting will include the employee's name and a reference to the specific location answering.",
    ],
)
def test_audited_non_radio_sentences_yield_no_procedure(line):
    assert parse_procedure_blocks([TextBlock("p.1", line)]) == []


def test_radio_procedure_still_extracted():
    line = "Personnel making a traffic stop will inform the radio dispatcher that they are stopping a vehicle, then transmit the location."
    procs = {c.procedure for c in parse_procedure_blocks([TextBlock("p.6", line)])}
    assert "traffic_stop" in procs and "location_address" in procs


def test_topic_must_be_governed_by_a_communication_verb():
    import re

    topic = re.compile(r"\blocation\b", re.I)
    assert governed_by_comm_verb("personnel shall advise the RDC of their location", topic)
    assert not governed_by_comm_verb("an employee shall be sent to the location if known", topic)
    assert not governed_by_comm_verb("Police Radio will notify a supervisor to take the officer's location", topic)


def test_sentence_split_breaks_on_lowercase_enumerators():
    """Chicago: an unrelated next instruction was welded onto the rule."""
    text = "Once acknowledgement is given, there will be tacit approval. j. request air support if available. 2."
    parts = split_sentences(text)
    assert len(parts) >= 2
    assert not any("request air support" in p and "tacit approval" in p for p in parts)


def test_numeric_trigger_does_not_match_the_word_digital():
    line = "Personnel will request that the Digital Vehicular Repeating System be transported to their location."
    assert "numeric" not in {c.procedure for c in parse_procedure_blocks([TextBlock("p.26", line)])}


# ---------------------------------------------------------------- locators and provenance


def test_layout_locators_are_stable_and_more_precise_than_a_page():
    doc = layout("lx01_multicolumn_code_table.pdf")
    again = layout("lx01_multicolumn_code_table.pdf")
    assert [b.locator for b in doc.included_blocks()] == [b.locator for b in again.included_blocks()]
    cell = next(b for b in doc.included_blocks() if b.block_type is BlockType.TABLE_CELL)
    assert cell.locator.startswith("p.1:tbl[")
    assert "@(" in cell.locator and cell.locator != "p.1"


def test_every_candidate_records_its_structural_reason_and_parser_version():
    for c in parse_codes(layout("lx01_multicolumn_code_table.pdf")):
        assert c.structural_reason and c.evidence and c.parser_version
    for p in parse_phonetics(layout("lx04_local_alphabet_divergence.pdf")):
        assert p.structural_reason and p.parser_version


# ---------------------------------------------------------------- cache


def test_cache_key_changes_when_layout_code_changes(tmp_path):
    doc = layout("lx09_single_column_narrative.pdf")
    digest = "sha256:" + "a" * 64
    layout_cache.save(doc, tmp_path, digest)
    assert layout_cache.load(tmp_path, digest) is not None
    stale = layout_cache.cache_path(tmp_path, digest, fingerprint="deadbeefdeadbeef")
    assert not stale.exists()
    assert layout_cache.cache_key(digest, fingerprint="deadbeefdeadbeef") != layout_cache.cache_key(digest)
    assert LAYOUT_VERSION in layout_cache.cache_key(digest)
    assert layout_code_fingerprint() in layout_cache.cache_key(digest)


def test_cache_rejects_entry_written_for_a_different_document(tmp_path):
    doc = layout("lx09_single_column_narrative.pdf")
    layout_cache.save(doc, tmp_path, "sha256:" + "b" * 64)
    assert layout_cache.load(tmp_path, "sha256:" + "c" * 64) is None


def test_cache_roundtrip_preserves_structure(tmp_path):
    doc = layout("lx01_multicolumn_code_table.pdf")
    digest = "sha256:" + "d" * 64
    layout_cache.save(doc, tmp_path, digest)
    restored = layout_cache.load(tmp_path, digest)
    assert restored is not None
    assert [b.locator for b in restored.included_blocks()] == [b.locator for b in doc.included_blocks()]
    assert parse_codes(restored) == parse_codes(doc)


# ---------------------------------------------------------------- isolation


def test_malformed_pdf_raises_rather_than_returning_empty_layout():
    with pytest.raises(ValueError):
        layout_for(b"%PDF-broken", "application/pdf")


def test_html_layout_keeps_table_identity():
    doc = layout_for(b"<html><body><table><tr><td>10-4</td><td>Acknowledged</td></tr></table></body></html>", "text/html")
    cells = [b for b in doc.included_blocks() if b.block_type is BlockType.TABLE_CELL]
    assert len(cells) == 2
    assert cells[0].table_id == 1 and cells[0].row_id == 1 and cells[0].cell_id == 1


# ---------------------------------------------------------------- evaluation harness


def test_gold_labels_derive_from_the_independent_audit_without_modifying_it():
    gold = build_gold(AUDIT / "fact_audit.jsonl", AUDIT / "real_facts.jsonl", AUDIT / "real_sources.jsonl")
    assert len(gold) == 116
    assert {g.reviewer for g in gold} == {"GPT-6 Astra independent source review"}
    assert all(g.label_source == "derived_from_independent_audit" and g.derivation_rule for g in gold)
    assert sum(1 for g in gold if g.label == Label.TRUE_FACT) == 24
    original = [json.loads(line) for line in (AUDIT / "fact_audit.jsonl").read_text().splitlines() if line.strip()]
    assert len(original) == 116, "the committed audit file must not be rewritten"


def test_label_derivation_rules():
    def flags(meaning: bool, normalized: bool, scope: bool, reason: str = "") -> dict:
        return {
            "exact_meaning_supported": meaning,
            "normalized_metadata_correct": normalized,
            "applicability_scope_correct": scope,
            "reason": reason,
        }

    assert derive_label(flags(True, True, True))[0] == Label.TRUE_FACT
    assert derive_label(flags(True, True, False))[0] == Label.WRONG_SCOPE
    assert derive_label(flags(True, False, False))[0] == Label.WRONG_NORMALIZATION
    assert derive_label({"exact_meaning_supported": False, "reason": "Revision date misread"})[0] == Label.FALSE_POSITIVE
    assert derive_label({"exact_meaning_supported": False, "reason": "Omits the following exception"})[0] == Label.INSUFFICIENT_CONTEXT
    assert classify_failure("Multi-column bleed into code meaning", supported=False) == "LAYOUT_COLUMN_BLEED"
    assert classify_failure("Meaning matches inspected source", supported=True) == "NOT_A_FAILURE"


def test_replay_eliminates_every_audited_code_and_phonetic_false_positive():
    gold = build_gold(AUDIT / "fact_audit.jsonl", AUDIT / "real_facts.jsonl", AUDIT / "real_sources.jsonl")
    metrics = summarise(replay(gold))["by_fact_family"]
    for family in ("code_meaning", "phonetic_letter"):
        bucket = metrics[family]
        assert bucket["false_positives_eliminated"] == bucket["false_positives_total_in_gold"]
        assert bucket["replay_unsupported_still_emitted"] == 0


def test_replay_improves_procedure_precision():
    gold = build_gold(AUDIT / "fact_audit.jsonl", AUDIT / "real_facts.jsonl", AUDIT / "real_sources.jsonl")
    bucket = summarise(replay(gold))["by_fact_family"]["procedure_rule"]
    assert bucket["baseline_meaning_precision"] < 0.5
    assert bucket["replay_meaning_precision"] >= 0.9
    assert bucket["context_complete_meaning_precision"] == 1.0


def test_leave_one_document_out_folds_cover_every_document():
    gold = build_gold(AUDIT / "fact_audit.jsonl", AUDIT / "real_facts.jsonl", AUDIT / "real_sources.jsonl")
    outcomes = replay(gold)
    docs = sorted({o.document_key for o in outcomes})
    assert docs == ["CHI_CPD_DIRECTIVE", "CHP_AURAL_BREVITY", "IN_ISP_COMMUNICATIONS", "PHL_PPD_DIRECTIVE_7_1"]
    for held in docs:
        held_out = [o for o in outcomes if o.document_key == held]
        assert held_out, f"fold {held} is empty"
        assert summarise(held_out)["overall"]["audited_candidates"] == len(held_out)


def test_no_agency_specific_parser_branches():
    """A rule tuned to one agency is a failure, not a fix."""
    banned = [
        "philadelphia", "chicago", "indiana", "california highway", "chp", "phillypolice",
        "ppd", "cpd", "isp_", "oemc_", "can-s05", "can-s14", "can-m03", "can-m05",
    ]
    sources = [
        ROOT / "src/radiocorpus/extraction/codes.py",
        ROOT / "src/radiocorpus/extraction/phonetics.py",
        ROOT / "src/radiocorpus/extraction/procedures.py",
        ROOT / "src/radiocorpus/extraction/context.py",
        ROOT / "src/radiocorpus/layout/segment.py",
        ROOT / "src/radiocorpus/layout/backends.py",
        ROOT / "src/radiocorpus/layout/records.py",
    ]
    for path in sources:
        code = "\n".join(
            line for line in path.read_text().splitlines() if not line.strip().startswith("#")
        )
        body = code.split('"""')
        executable = "".join(body[::2]).lower()  # drop docstrings, keep code
        for token in banned:
            assert token not in executable, f"{path.name} contains an agency-specific token: {token}"
