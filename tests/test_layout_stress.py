"""Tests for the randomized layout corpus, the threshold sweep and the scanned-page gate.

These guard three weaknesses that were declared but unmeasured in the first handoff: the
fixtures were self-designed, the column thresholds were fitted to one adversarial layout, and
the OCR gate had never been exercised against a page with no text layer.

Nothing here says anything about real documents. The corpus is synthetic, its ground truth is
known only because this code generated it, and the four real validation documents remain
unretrieved.
"""

from __future__ import annotations

import pytest

from radiocorpus.evaluation.pdfwrite import scanned_pdf, text_width, wrap_exact
from radiocorpus.evaluation.sensitivity import Setting, sweep
from radiocorpus.evaluation.stress import evaluate, plan, plan_overflow, render, run
from radiocorpus.extraction.codes import parse_codes
from radiocorpus.extraction.phonetics import parse_phonetics
from radiocorpus.extraction.procedures import parse_procedures
from radiocorpus.extraction.text import OCRRequired
from radiocorpus.layout.backends import MIN_NATIVE_CHARS, layout_for

# Small but fixed. The published measurements use a larger range; these seeds keep the suite
# quick while still covering every arrangement the generator can draw.
SEEDS = range(1, 61)


# ---------------------------------------------------------------- the generator itself


def test_plans_are_deterministic():
    """A seed must mean one document forever, or no measurement is reproducible."""
    assert plan(7) == plan(7)
    assert render(plan(7)) == render(plan(7))
    assert plan(7) != plan(8)


def test_no_plan_places_text_outside_its_column():
    """A page whose columns overlap is geometry no document has.

    Scoring column detection on such a page measures the generator's arithmetic, not the
    parser. This caught a real error: an approximate character width let long lines overflow,
    which then showed up as a column-detection failure that was nothing of the kind.
    """
    for seed in SEEDS:
        assert plan_overflow(plan(seed)) == [], f"seed {seed} renders outside its column"


def test_exact_wrapping_never_exceeds_the_column():
    line = "Beacon acknowledged for the second shift pending confirmation at the north gate"
    for width in (60.0, 120.0, 250.0):
        for size in (7.0, 9.0, 12.0):
            for part in wrap_exact(line, size, width):
                if len(part.split()) == 1:
                    continue  # a single word wider than the column cannot be broken further
                assert text_width(part, size) <= width + 0.01


# ---------------------------------------------------------------- what the corpus shows


def test_column_detection_never_invents_a_column():
    """The asymmetry the layout layer is built on.

    Merging two columns loses facts from one table. Inventing a column corrupts every line on
    the page, so this direction is a hard failure rather than a score.
    """
    results, summary = run(SEEDS)
    assert summary["invented_columns"] == 0, [r.seed for r in results if r.column_verdict == "invented_columns"]


def test_no_date_decoy_is_ever_emitted_as_a_code():
    """Known failure A, generalised: every document carries code-shaped revision dates."""
    _, summary = run(SEEDS)
    assert summary["decoy_dates_emitted_as_codes"] == 0


def test_no_procedure_is_emitted_from_a_document_with_no_radio_act():
    """Known failure E, generalised: paperwork wording must not become a radio rule."""
    _, summary = run(SEEDS)
    assert summary["procedure_false_positive_documents"] == 0


def test_code_and_phonetic_precision_hold_on_unseen_geometry():
    """Precision is reported with coverage: a parser that emits nothing has useless precision."""
    _, summary = run(SEEDS)
    assert summary["code_meaning"]["tp"] > 0
    assert summary["phonetic_letter"]["tp"] > 0
    assert summary["code_meaning"]["precision"] >= 0.95
    assert summary["phonetic_letter"]["precision"] >= 0.95
    assert summary["code_meaning"]["recall"] >= 0.90
    assert summary["phonetic_letter"]["recall"] >= 0.90


def test_layout_never_raises_on_generated_geometry():
    _, summary = run(SEEDS)
    assert summary["layout_errors"] == 0


# ---------------------------------------------------------------- the specific defects found


def test_one_column_alphabet_is_recovered():
    """A one-column alphabet prints as short all-caps lines, which the layout layer types as
    headings. Dropping every heading lost all 26 letters; the hand-written fixture happened to
    be two-column and never exercised this path."""
    single = next(
        p for p in (plan(s) for s in range(1, 400)) if p.kind == "alphabet" and p.n_columns == 1 and not p.heading
    )
    letters = parse_phonetics(layout_for(render(single), "application/pdf"))
    assert {c.letter for c in letters} == {letter for letter, _ in single.letters}
    assert all(c.structural_reason in {"PHONETIC_HEADING", "ALPHABET_RUN", "LETTER_SEQUENCE"} for c in letters)


def test_enumerated_headings_still_yield_no_phonetics():
    """The counterpart: recovering one-column alphabets must not reopen known failure B."""
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "layout" / "lx03_enumerated_headings.pdf"
    assert parse_phonetics(layout_for(fixture.read_bytes(), "application/pdf")) == []


def test_wrapped_meaning_cell_is_not_truncated():
    """A meaning that wraps in a two-cell row was cut at the first line.

    A truncated meaning is a wrong fact, not a partial one, so this is the direction that
    matters most.
    """
    paired = next(
        p
        for p in (plan(s) for s in range(1, 400))
        if p.arrangement == "paired_columns" and any(len(wrap_exact(m, p.font_size, p.column_width)) > 1 for _, m in p.codes)
    )
    result = evaluate(paired)
    assert result.code_fp == 0, "a wrapped cell produced a wrong meaning"


# ---------------------------------------------------------------- threshold sensitivity


def test_the_thresholds_in_use_are_not_overfitted():
    """The values in use must sit on the safe plateau, not on a peak found by fitting.

    A setting is unusable if it invents a column on any document, whatever its exact-match
    rate, so the comparison is made only against settings that never do.
    """
    out = sweep(range(1, 41))
    in_use = out["settings"][out["in_use"]]
    assert in_use["invented_columns"] == 0
    usable = [v["exact_rate"] for v in out["settings"].values() if v["usable"]]
    assert in_use["exact_rate"] >= max(usable) - 1e-9


def test_a_permissive_occupancy_tolerance_invents_columns():
    """Evidence that the tolerance is the sensitive parameter, and which way it fails."""
    out = sweep(range(1, 121), [Setting(6.0, 0.15, 3), Setting(6.0, 0.3, 2)])
    assert out["settings"]["gutter=6pt,tolerance=0.15,rows=3"]["invented_columns"] == 0
    assert out["settings"]["gutter=6pt,tolerance=0.3,rows=2"]["invented_columns"] > 0


# ---------------------------------------------------------------- the scanned-page gate


def test_scanned_page_refuses_rather_than_returning_empty_layout():
    """A page with an image and no text layer must fail closed, not parse as a blank page."""
    with pytest.raises(OCRRequired):
        layout_for(scanned_pdf(), "application/pdf")


def test_scanned_page_yields_no_candidates_at_all():
    for parser in (parse_codes, parse_phonetics, parse_procedures):
        with pytest.raises(OCRRequired):
            parser(layout_for(scanned_pdf(), "application/pdf"))


def test_image_page_with_enough_native_text_is_not_refused():
    """The gate keys on the absence of text, not on the presence of an image."""
    caption = "Members will advise the dispatcher over the radio before leaving the assignment."
    assert len(caption) >= MIN_NATIVE_CHARS
    doc = layout_for(scanned_pdf(caption=caption), "application/pdf")
    assert any(b.text for p in doc.pages for b in p.blocks)
    assert all(p.text_extraction_method == "native_pdf_text" for p in doc.pages)


def test_supplied_ocr_is_represented_without_invented_structure():
    """OCR returns text with no geometry. It must not be dressed up as a table."""

    class FakeOCR:
        def extract_page(self, data, page):  # noqa: ARG002 - interface fixed by the caller
            return "10-4 Message received\n10-8 In service\n10-9 Repeat transmission"

    doc = layout_for(scanned_pdf(), "application/pdf", ocr=FakeOCR())
    assert [p.text_extraction_method for p in doc.pages] == ["ocr"]
    blocks = doc.included_blocks()
    assert blocks and all(b.table_id is None and b.cell_id is None for b in blocks)
    assert all(b.backend == "ocr" for b in blocks)


def test_ocr_returning_nothing_still_refuses():
    class EmptyOCR:
        def extract_page(self, data, page):  # noqa: ARG002 - interface fixed by the caller
            return "   "

    with pytest.raises(OCRRequired):
        layout_for(scanned_pdf(), "application/pdf", ocr=EmptyOCR())
