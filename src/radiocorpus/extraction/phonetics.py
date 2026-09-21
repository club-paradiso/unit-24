"""Structure-gated phonetic-alphabet parser.

A string shaped like ``LETTER + WORD`` is not a phonetic mapping. In the audited corpus the
enumerated section headings ``C. COMMUNICATIONS``, ``A. Attempt to Locate`` and
``B. Broadcasts`` were all read as phonetic pairs. A mapping is now emitted only when the
surrounding structure shows an alphabet: an explicit heading, a table of pairs, a run of
distinct letters in one region, or a region that is almost entirely letter-and-word pairs.

That last route exists because a one-column alphabet prints as a column of short all-capital
lines, which the layout layer types as headings on typography alone; skipping every heading
lost all 26 letters of such a listing. It is gated on density rather than on a letter count,
so a directive page with a handful of lettered section titles cannot reach it.

Reference alphabets are used to *describe* what was found and never to change it. If a local
alphabet differs from APCO on one letter, all 26 local mappings are preserved and the
divergence is reported.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from radiocorpus.extraction.text import TextBlock
from radiocorpus.layout.model import BlockType, DocumentLayout, LayoutBlock
from radiocorpus.layout.segment import ENUMERATOR

PARSER_RULE = "phonetic_letter:structural"
PARSER_VERSION = "4"

NATO = {
    "A": "ALFA", "B": "BRAVO", "C": "CHARLIE", "D": "DELTA", "E": "ECHO", "F": "FOXTROT",
    "G": "GOLF", "H": "HOTEL", "I": "INDIA", "J": "JULIETT", "K": "KILO", "L": "LIMA",
    "M": "MIKE", "N": "NOVEMBER", "O": "OSCAR", "P": "PAPA", "Q": "QUEBEC", "R": "ROMEO",
    "S": "SIERRA", "T": "TANGO", "U": "UNIFORM", "V": "VICTOR", "W": "WHISKEY", "X": "XRAY",
    "Y": "YANKEE", "Z": "ZULU",
}
NATO_VARIANTS = {"ALPHA": "ALFA", "JULIET": "JULIETT", "X-RAY": "XRAY"}
APCO_1941 = {
    "A": "ADAM", "B": "BOY", "C": "CHARLES", "D": "DAVID", "E": "EDWARD", "F": "FRANK",
    "G": "GEORGE", "H": "HENRY", "I": "IDA", "J": "JOHN", "K": "KING", "L": "LINCOLN",
    "M": "MARY", "N": "NORA", "O": "OCEAN", "P": "PAUL", "Q": "QUEEN", "R": "ROBERT",
    "S": "SAM", "T": "TOM", "U": "UNION", "V": "VICTOR", "W": "WILLIAM", "X": "XRAY",
    "Y": "YOUNG", "Z": "ZEBRA",
}
REFERENCE_ALPHABETS = {"NATO": NATO, "APCO_1941": APCO_1941}

# Minimum distinct letters paired within one region before it may be called an alphabet.
MIN_REGION_LETTERS = 4
# A one-column alphabet prints as a run of short all-caps lines, which the layout layer calls
# headings on typography alone. Such a region may still be an alphabet, but only on much
# stronger evidence than a four-letter run: most of the region must *be* the listing.
MIN_HEADING_RUN_LETTERS = 8
MIN_HEADING_RUN_DENSITY = 0.5
# Letters needed before a system label may be offered at all.
MIN_LABEL_LETTERS = 13
LABEL_MATCH_RATIO = 0.9

PHONETIC_HEADING = re.compile(
    r"\bphonetic\b|\balphabet\b|\bspelling (?:table|guide|key)\b|\bletter (?:code|equivalents?)\b|"
    r"\bapco\b|\bnato\b|\bint(?:ernational)? (?:radiotelephony )?spelling\b",
    re.I,
)
_PAIR = re.compile(
    r"(?<![A-Za-z])(?P<letter>[A-Z])\s*(?:[-–:=|]|\s)\s*(?P<word>[A-Z][a-z]{2,14}|[A-Z]{3,14}|X-?[Rr]ay)(?![A-Za-z])"
)
_PAIR_REV = re.compile(r"(?P<word>[A-Z][a-z]{2,14}|[A-Z]{3,14})\s*\(\s*(?P<letter>[A-Z])\s*\)")
# "C. COMMUNICATIONS FAILURE:" and "A. Attempt to Locate ..." — an enumerated clause.
_ENUM_PAIR = re.compile(r"^\s*[A-Za-z]\s*[.)]\s+\S")
_SENTENCE_TAIL = re.compile(r"\b(?:the|of|to|for|and|is|are|shall|will|must|a|an|in|on|by)\b", re.I)
# Margin change-bars and bullets that precede an enumerator in revised policy documents
# ("*5  C. COMMUNICATIONS FAILURE:"). Stripped only for structural tests, never from text.
_MARGIN_MARKER = re.compile(r"^[\s*\u2022\u00b7\u25aa\u25cf\u2013-]*(?:\d{1,3})?[\s*\u2022\u00b7\u25aa\u25cf]*")


@dataclass(frozen=True)
class PhoneticCandidate:
    letter: str
    word: str
    locator: str
    excerpt: str
    structural_reason: str = "text_only"
    evidence: tuple[str, ...] = ()
    region_id: str = ""
    parser_rule: str = PARSER_RULE
    parser_version: str = PARSER_VERSION
    page_number: int | None = None


@dataclass
class AlphabetReport:
    """What was actually found, plus how it compares to reference alphabets."""

    label: str = "UNKNOWN"
    coverage: float = 0.0
    mappings: dict[str, str] = field(default_factory=dict)
    divergences: dict[str, dict[str, str]] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "coverage": round(self.coverage, 4),
            "mappings": dict(sorted(self.mappings.items())),
            "divergences": {k: dict(sorted(v.items())) for k, v in sorted(self.divergences.items())},
            "evidence": list(self.evidence),
        }


def _clean(word: str) -> str:
    w = word.upper().replace("-", "")
    return NATO_VARIANTS.get(w, w)


def strip_margin_marker(text: str) -> str:
    """Remove revision change-bars so an enumerator can still be recognised behind them."""
    m = _MARGIN_MARKER.match(text)
    return text[m.end() :] if m else text


def _is_enumerated_clause(text: str) -> bool:
    """True when the letter is a list enumerator introducing prose, not a phonetic word."""
    text = strip_margin_marker(text)
    if not _ENUM_PAIR.match(text):
        return False
    rest = text[ENUMERATOR.match(text).end() :] if ENUMERATOR.match(text) else ""
    words = rest.split()
    # "C. COMMUNICATIONS FAILURE:" -> 2 words; "A. Attempt to Locate ..." -> many.
    return len(words) >= 2 or bool(_SENTENCE_TAIL.search(rest)) or rest.rstrip().endswith(":")


def _region_of(block: LayoutBlock) -> str:
    """Blocks share a region when they could plausibly be one alphabet listing."""
    if block.table_id is not None:
        return f"p{block.page_number}:tbl{block.table_id}"
    if block.column_id is not None:
        return f"p{block.page_number}:col{block.column_id}"
    return f"p{block.page_number}"


def _pairs_in(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in list(_PAIR.finditer(text)) + list(_PAIR_REV.finditer(text)):
        letter, word = m["letter"].upper(), _clean(m["word"])
        if not word.startswith(letter):
            continue  # a phonetic word begins with its own letter
        out.append((letter, word))
    return out


def parse_phonetics(layout: DocumentLayout) -> list[PhoneticCandidate]:
    """Emit letter mappings only where an alphabet is structurally evident."""
    blocks = layout.included_blocks()
    headings_by_page: dict[int, list[LayoutBlock]] = defaultdict(list)
    for b in blocks:
        if b.block_type is BlockType.HEADING and PHONETIC_HEADING.search(b.text):
            headings_by_page[b.page_number].append(b)

    # Collect candidate pairs per region, rejecting enumerated clauses outright.
    per_region: dict[str, list[tuple[LayoutBlock, str, str]]] = defaultdict(list)

    # Row-wise pairing: a cell holding just a letter beside a cell holding its word. HTML
    # tables and ruled PDF tables both present alphabets this way, and neither puts the pair
    # inside a single block.
    by_row: dict[tuple[int, int, int], list[LayoutBlock]] = {}
    paired: set[int] = set()
    for b in blocks:
        if b.table_id is not None and b.row_id is not None and b.cell_id is not None:
            by_row.setdefault((b.page_number, b.table_id, b.row_id), []).append(b)
    for cells in by_row.values():
        cells.sort(key=lambda c: (c.cell_id if c.cell_id is not None else 0))
        for i, cell in enumerate(cells[:-1]):
            letter = cell.text.strip().upper().rstrip(".:-")
            if len(letter) != 1 or not letter.isalpha():
                continue
            word = _clean(cells[i + 1].text.strip())
            if not re.fullmatch(r"[A-Z][A-Z-]{2,14}", word) or not word.startswith(letter):
                continue
            per_region[_region_of(cell)].append((cell, letter, word))
            paired.add(id(cell))
            paired.add(id(cells[i + 1]))

    # A block the layout layer typed as a heading may still be one entry of a one-column
    # alphabet: every line of such a listing is short and all-caps, which is all the layer
    # judges on. The pairs are collected, but marked, so the region gate below can demand
    # stronger evidence for them than for ordinary body text.
    region_blocks: dict[str, int] = defaultdict(int)
    heading_sourced: dict[str, int] = defaultdict(int)

    for b in blocks:
        region_blocks[_region_of(b)] += 1
        if id(b) in paired:
            continue
        if b.block_type is BlockType.HEADING and PHONETIC_HEADING.search(b.text):
            continue  # the alphabet heading itself is not one of its own entries
        if _is_enumerated_clause(b.text):
            continue
        found = False
        for line in b.text.splitlines():
            if _is_enumerated_clause(line):
                continue
            for letter, word in _pairs_in(line):
                per_region[_region_of(b)].append((b, letter, word))
                found = True
        if found and b.block_type is BlockType.HEADING:
            heading_sourced[_region_of(b)] += 1

    out: list[PhoneticCandidate] = []
    seen: set[tuple[str, str]] = set()
    for region, items in sorted(per_region.items()):
        distinct = {letter for _, letter, _ in items}
        governing = None
        for b, _, _ in items:
            for h in headings_by_page.get(b.page_number, ()):
                if h.reading_order < b.reading_order and (governing is None or h.reading_order > governing.reading_order):
                    governing = h
        table_pairs = sum(1 for b, _, _ in items if b.block_type is BlockType.TABLE_CELL)
        body_letters = {letter for b, letter, _ in items if b.block_type is not BlockType.HEADING}
        pair_blocks = len({id(b) for b, _, _ in items})
        density = pair_blocks / region_blocks[region] if region_blocks.get(region) else 0.0
        reason: str | None = None
        evidence: list[str] = [f"region:{region}", f"distinct_letters:{len(distinct)}"]
        if governing is not None:
            reason = "PHONETIC_HEADING"
            evidence.append(f"heading:{governing.text[:60]!r}")
        elif len(distinct) >= MIN_REGION_LETTERS and table_pairs >= MIN_REGION_LETTERS:
            reason = "ALPHABET_TABLE"
            evidence.append(f"table_pairs:{table_pairs}")
        elif len(body_letters) >= MIN_REGION_LETTERS:
            reason = "LETTER_SEQUENCE"
        elif (
            heading_sourced.get(region)
            and len(distinct) >= MIN_HEADING_RUN_LETTERS
            and density >= MIN_HEADING_RUN_DENSITY
        ):
            # Almost every block in this region is a letter-and-word pair. A directive page
            # whose sections happen to start with letters is a handful of such lines among
            # many paragraphs and cannot reach this density; a printed alphabet always does.
            reason = "ALPHABET_RUN"
            evidence.append(f"pair_block_density:{density:.2f}")
        if reason is None:
            continue
        for b, letter, word in items:
            if (letter, word) in seen:
                continue
            seen.add((letter, word))
            out.append(
                PhoneticCandidate(
                    letter=letter,
                    word=word,
                    locator=b.locator,
                    excerpt=b.text.strip()[:300],
                    structural_reason=reason,
                    evidence=tuple(evidence) + tuple(b.structural_evidence),
                    region_id=region,
                    page_number=b.page_number,
                )
            )
    out.sort(key=lambda c: (c.page_number or 0, c.letter, c.word))
    return out


def describe_alphabet(cands: list[PhoneticCandidate]) -> AlphabetReport:
    """Describe the recovered alphabet. Local mappings are never rewritten to match a reference."""
    report = AlphabetReport()
    mappings: dict[str, str] = {}
    conflicts: dict[str, set[str]] = defaultdict(set)
    for c in cands:
        conflicts[c.letter].add(c.word)
        mappings.setdefault(c.letter, c.word)
    report.mappings = mappings
    report.coverage = len(mappings) / 26 if mappings else 0.0
    for letter, words in sorted(conflicts.items()):
        if len(words) > 1:
            report.evidence.append(f"multiple_words_for_{letter}:{sorted(words)}")
    if len(mappings) < MIN_LABEL_LETTERS:
        report.label = "UNKNOWN"
        report.evidence.append(f"too_few_letters_for_label:{len(mappings)}")
        return report
    best_label, best_ratio = "LOCAL", 0.0
    for name, ref in REFERENCE_ALPHABETS.items():
        matched = sum(1 for k, v in mappings.items() if ref.get(k) == v)
        ratio = matched / len(mappings)
        if ratio > best_ratio:
            best_label, best_ratio = name, ratio
    if best_ratio >= LABEL_MATCH_RATIO:
        report.label = best_label
        ref = REFERENCE_ALPHABETS[best_label]
        divergent = {k: {"local": v, "reference": ref.get(k, "")} for k, v in mappings.items() if ref.get(k) != v}
        report.divergences = divergent
        report.evidence.append(f"label_match_ratio:{best_ratio:.3f}")
        if divergent:
            # The label is descriptive metadata only; the local words stand as extracted.
            report.evidence.append(f"local_divergences_preserved:{sorted(divergent)}")
    else:
        report.label = "LOCAL"
        report.evidence.append(f"best_reference={best_label} ratio={best_ratio:.3f} below {LABEL_MATCH_RATIO}")
    return report


def parse_phonetic_blocks(blocks: list[TextBlock]) -> list[PhoneticCandidate]:
    """Legacy entry point operating on flattened text."""
    from radiocorpus.extraction.codes import _layout_from_text_blocks

    return parse_phonetics(_layout_from_text_blocks(blocks))


def label_system(cands: list[PhoneticCandidate]) -> tuple[str, float]:
    """Backward-compatible summary. Prefer :func:`describe_alphabet`, which reports divergence."""
    r = describe_alphabet(cands)
    return r.label, r.coverage


__all__ = [
    "APCO_1941",
    "NATO",
    "AlphabetReport",
    "PhoneticCandidate",
    "describe_alphabet",
    "label_system",
    "parse_phonetic_blocks",
    "parse_phonetics",
]
