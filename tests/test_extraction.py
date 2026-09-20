from radiocorpus.extraction.codes import normalize_code, parse_code_blocks
from radiocorpus.extraction.llm import parse_model_output
from radiocorpus.extraction.phonetics import label_system, parse_phonetic_blocks
from radiocorpus.extraction.procedures import parse_procedure_blocks
from radiocorpus.extraction.text import TextBlock, blocks_for
from tests.conftest import FIXTURES


def test_html_table_codes_with_locators():
    blocks = blocks_for((FIXTURES / "fx001_exampleville_policy_4_10_2024.html").read_bytes(), "text/html")
    cands = parse_code_blocks(blocks)
    by = {c.code: c for c in cands}
    assert by["10-50"].meaning == "Traffic collision" and by["10-50"].locator.startswith("html:table[1]>tr[")
    assert by["10-9"].meaning == "Repeat last transmission"
    assert all(c.excerpt and len(c.excerpt) <= 200 for c in cands)


def test_pdf_codes_and_effective_line():
    blocks = blocks_for((FIXTURES / "fx001_exampleville_general_order_2009.pdf").read_bytes(), "application/pdf")
    cands = parse_code_blocks(blocks)
    assert {c.code: c.meaning for c in cands}["10-50"] == "Vehicle accident"
    assert cands[0].locator == "p.1"


def test_signal_codes():
    blocks = [TextBlock("p.1", "Signal 7  Dead person\nSignal 20 Mental subject\nCode 3 Emergency response")]
    got = {c.code: (c.code_system, c.meaning) for c in parse_code_blocks(blocks)}
    assert got["SIGNAL 7"] == ("SIGNAL", "Dead person")
    assert got["CODE 3"] == ("CODE", "Emergency response")


def test_code_parser_edge_cases():
    blocks = [
        TextBlock("p.2", "See Section 10-4 for details\n10-4\n10-4:Acknowledged\n10 - 8   In service   10-97 Arrived on scene\nRev 10-2019 Policy")
    ]
    got = {c.code: c.meaning for c in parse_code_blocks(blocks)}
    assert got.get("10-4") == "Acknowledged"  # bare "10-4" and "Section 10-4" produce nothing
    assert got.get("10-8") == "In service" and got.get("10-97") == "Arrived on scene"
    assert normalize_code("10 - 8") == ("TEN_CODE", "10-8")
    assert normalize_code("signal-7") == ("SIGNAL", "SIGNAL 7")


def test_phonetic_apco_and_nato_labels():
    html = blocks_for((FIXTURES / "fx001_exampleville_policy_4_10_2024.html").read_bytes(), "text/html")
    ph = parse_phonetic_blocks(html)
    assert {c.letter for c in ph} == set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert label_system(ph)[0] == "APCO_1941"
    pdf = blocks_for((FIXTURES / "fx002_example_county_so_policy_undated.pdf").read_bytes(), "application/pdf")
    ph2 = parse_phonetic_blocks(pdf)
    assert label_system(ph2) == ("NATO", 1.0)
    assert {c.word for c in ph2 if c.letter == "X"} == {"XRAY"}


def test_phonetic_noise_rejected():
    blocks = [TextBlock("p.1", "B Adam\nQ Section\nA Alpha")]
    got = {(c.letter, c.word) for c in parse_phonetic_blocks(blocks)}
    assert got == {("A", "ALFA")}  # word must start with its letter; 'Alpha' normalised to NATO spelling


def test_procedure_spotter_is_prescriptive_only():
    blocks = [
        TextBlock("html:p[1]", "Units shall read back all license plate numbers to the dispatcher. The weather was nice. Officers may use radios.")
    ]
    got = parse_procedure_blocks(blocks)
    procs = {c.procedure for c in got}
    assert "readback" in procs and "vehicle_plate" in procs
    assert all("weather" not in c.rule_text for c in got)


def test_model_output_parser_drops_unlocated_claims():
    raw = (
        'noise [{"fact_type":"code_meaning","payload":{"code_system":"TEN_CODE","code":"10-4","meaning":"Ack"},"locator":"p.1","excerpt":"10-4 Ack"},'
        '{"fact_type":"code_meaning","payload":{"code":"10-5"},"locator":"p.99","excerpt":"x"},'
        '{"fact_type":"code_meaning","payload":{"code":"10-6"},"locator":"p.1"}] trailing'
    )
    out = parse_model_output(raw, "m", {"p.1"})
    assert len(out) == 1 and out[0].locator == "p.1" and out[0].model == "m"
    assert parse_model_output("not json", "m", {"p.1"}) == []


def test_text_blocks_plain_text_fallback():
    blocks = blocks_for(b"line one\n\nline two", None)
    assert [b.locator for b in blocks] == ["line.1", "line.3"]
