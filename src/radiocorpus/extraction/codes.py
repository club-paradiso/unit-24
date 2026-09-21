"""Structure-gated parser for code tables (10-codes, 11-codes, signal/status/disposition codes).

The previous version searched flattened lines for anything shaped like a code and took the
rest of the line as its meaning. On real documents that produced a revision date read as an
eleven-code, and multi-column tables whose neighbouring columns bled into each other.

This version requires *structural* support before it will emit anything:

``TABLE_CELL_PAIR``      the code sits alone in a cell and the meaning in the adjacent cell
``COLUMN_SERIES``        three or more records in one column lane each open with a code token
``CODE_TABLE_HEADING``   a heading naming a code list governs the block

A regex resemblance on its own is never sufficient. Dates, statutory citations, structural
cross-references and telephone numbers are rejected by shape, not by literal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from radiocorpus.extraction.context import (
    PHONE_LIKE,
    STATUTE,
    STRUCTURAL_REF,
    in_date_context,
    numeric_token_is_date,
)
from radiocorpus.extraction.text import TextBlock, squash
from radiocorpus.layout.model import BlockType, DocumentLayout, LayoutBlock, layout_from_text
from radiocorpus.layout.records import assemble_records

PARSER_RULE = "code_meaning:structural"
PARSER_VERSION = "4"

MIN_SERIES = 3  # records in one lane before an unheaded list counts as a code table
MAX_MEANING_CHARS = 160

# The code token itself. Anchored uses require it at the start of a record.
CODE_TOKEN = re.compile(
    r"(?P<code>(?:10|11|12|13)\s?-\s?\d{1,3}[A-Za-z]?|(?:Code|Signal|Status)\s?-?\s?\d{1,3}[A-Za-z]?)",
    re.I,
)
CODE_AT_START = re.compile(r"^\s*" + CODE_TOKEN.pattern + r"\s*(?P<sep>[:\-–|.]?)\s*(?P<meaning>.*)$", re.I)
PURE_CODE = re.compile(r"^\s*" + CODE_TOKEN.pattern + r"\s*[:.\-]?\s*$", re.I)

CODE_TABLE_HEADING = re.compile(
    r"\b(?:ten|10)[- ]?codes?\b|\beleven|11[- ]?codes?\b|\bradio codes?\b|\bbrevity\b|\bsignal codes?\b|"
    r"\bstatus codes?\b|\bdisposition codes?\b|\bcode list\b|\bcodes? and (?:their )?meanings?\b|\baural brevity\b",
    re.I,
)
_TRAILING_NOISE = re.compile(r"[\s.;,:–-]+$")


@dataclass(frozen=True)
class CodeCandidate:
    code_system: str
    code: str
    meaning: str
    raw: str
    locator: str
    excerpt: str
    structural_reason: str = "text_only"
    evidence: tuple[str, ...] = ()
    parser_rule: str = PARSER_RULE
    parser_version: str = PARSER_VERSION
    continuation_lines: int = 0
    page_number: int | None = None


def normalize_code(code: str) -> tuple[str, str]:
    c = squash(code).upper().replace(" -", "-").replace("- ", "-").replace(" ", "")
    if c.startswith("10-"):
        return "TEN_CODE", c
    if c.startswith("11-"):
        return "ELEVEN_CODE", c
    if c.startswith("12-") or c.startswith("13-"):
        return "OTHER", c
    m = re.match(r"(CODE|SIGNAL|STATUS)-?(\d{1,3}[A-Z]?)", c)
    if m:
        return m[1], f"{m[1]} {m[2]}"
    return "OTHER", c


def _rejects(text: str, m: re.Match[str]) -> str | None:
    """Reason to refuse a code-shaped span, or None when the shape survives."""
    if numeric_token_is_date(text, m.start("code"), m.end("code")):
        return "date_like_number"
    if in_date_context(text, m.start("code")):
        return "revision_or_issue_date_label"
    if PHONE_LIKE.search(text):
        return "telephone_number"
    before = text[: m.start("code")]
    if STRUCTURAL_REF.search(before):
        return "structural_cross_reference"
    if STATUTE.match(text[m.start("code") :]):
        return "statutory_citation"
    return None


def _clean_meaning(raw: str) -> str:
    meaning = squash(raw)
    # A statutory citation or a second code beginning in the same cell ends the meaning.
    cut = len(meaning)
    for m in CODE_TOKEN.finditer(meaning):
        if m.start() > 0:
            cut = min(cut, m.start())
            break
    st = STATUTE.search(meaning)
    if st and st.start() > 0:
        cut = min(cut, st.start())
    meaning = meaning[:cut]
    return _TRAILING_NOISE.sub("", meaning)[:MAX_MEANING_CHARS]


def _valid_meaning(meaning: str) -> bool:
    if len(meaning) < 3:
        return False
    if meaning.lower() in {"and", "or", "the", "n/a", "na", "none", "reserved", "not used", "unassigned"}:
        return False
    return bool(re.search(r"[A-Za-z]{3}", meaning))


CONTINUATION_GAP_FACTOR = 2.2  # multiples of line height before a vertical gap breaks a cell


def _cell_continuations(
    rows: dict[int, list[LayoutBlock]],
    row_id: int,
    meaning: LayoutBlock,
    *,
    key_cell_id: int,
    meaning_cell_id: int,
) -> list[LayoutBlock]:
    """Blocks that continue a wrapped meaning cell downwards.

    A meaning that wraps puts its remainder on the next visual row, in the same column, while
    that row's key column stays empty. That emptiness is the evidence, and it is generic: no
    knowledge of any particular document is used, only the shape of a two-column table.

    Without geometry nothing is joined, for the same reason record assembly refuses it: two
    lines cannot be shown to be neighbours without coordinates.
    """
    out: list[LayoutBlock] = []
    anchor = meaning
    for nxt_row in sorted(r for r in rows if r > row_id):
        cells = {c.cell_id: c for c in rows[nxt_row] if c.cell_id is not None}
        key = cells.get(key_cell_id)
        if key is not None and key.text.strip():
            break  # the key column speaks again: a new entry, not a continuation
        cont = cells.get(meaning_cell_id)
        if cont is None or not cont.text.strip():
            break
        if PURE_CODE.match(cont.text) or CODE_AT_START.match(cont.text):
            break  # a line that opens its own code is never a remainder
        if cont.bbox is None or anchor.bbox is None:
            break
        gap = cont.bbox.y0 - anchor.bbox.y1
        line_h = max(anchor.bbox.height, cont.bbox.height, 1.0)
        if gap > line_h * CONTINUATION_GAP_FACTOR or gap < -line_h:
            break
        out.append(cont)
        anchor = cont
    return out


def _heading_governs(block: LayoutBlock, headings: dict[int, list[LayoutBlock]]) -> LayoutBlock | None:
    """Nearest preceding heading on the same page that names a code list."""
    best: LayoutBlock | None = None
    for h in headings.get(block.page_number, ()):
        if h.reading_order < block.reading_order and CODE_TABLE_HEADING.search(h.text):
            if best is None or h.reading_order > best.reading_order:
                best = h
    return best


def parse_codes(layout: DocumentLayout) -> list[CodeCandidate]:
    """Extract code/meaning candidates that carry structural support."""
    blocks = layout.included_blocks()
    out: list[CodeCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    headings: dict[int, list[LayoutBlock]] = {}
    for b in blocks:
        if b.block_type is BlockType.HEADING:
            headings.setdefault(b.page_number, []).append(b)

    # ---- path 1: a cell holding only a code, paired with the next cell in the same row
    tables: dict[tuple[int, int], dict[int, list[LayoutBlock]]] = {}
    for b in blocks:
        if b.table_id is not None and b.row_id is not None and b.cell_id is not None:
            tables.setdefault((b.page_number, b.table_id), {}).setdefault(b.row_id, []).append(b)
    paired_blocks: set[int] = set()
    for rows in tables.values():
        for row_id in sorted(rows):
            cells = sorted(rows[row_id], key=lambda b: (b.cell_id if b.cell_id is not None else 0))
            for i, cell in enumerate(cells[:-1]):
                m = PURE_CODE.match(cell.text)
                if not m:
                    continue
                nxt = cells[i + 1]
                if PURE_CODE.match(nxt.text) or not nxt.text.strip():
                    continue
                if _rejects(cell.text, m):
                    continue
                # A meaning that wraps continues in the same column on rows whose key column
                # is empty. Without this the cell is truncated, and a truncated meaning is a
                # wrong fact rather than a partial one.
                continuations = _cell_continuations(
                    rows, row_id, nxt, key_cell_id=cell.cell_id, meaning_cell_id=nxt.cell_id
                )
                joined = " ".join([nxt.text.strip(), *(c.text.strip() for c in continuations)]).strip()
                meaning = _clean_meaning(joined)
                if not _valid_meaning(meaning):
                    continue
                system, code = normalize_code(m["code"])
                key = (cell.locator, code, meaning.lower())
                if key in seen:
                    continue
                seen.add(key)
                paired_blocks.add(id(cell))
                paired_blocks.add(id(nxt))
                evidence = list(cell.structural_evidence) + [f"paired_with:{nxt.locator}"]
                for c in continuations:
                    paired_blocks.add(id(c))
                if continuations:
                    evidence.append(f"cell_continuations:{len(continuations)}")
                out.append(
                    CodeCandidate(
                        code_system=system,
                        code=code,
                        meaning=meaning,
                        raw=f"{cell.text.strip()} {joined}"[:200],
                        locator=cell.locator,
                        excerpt=f"{cell.text.strip()} | {joined}"[:300],
                        structural_reason="TABLE_CELL_PAIR",
                        evidence=tuple(evidence),
                        continuation_lines=len(continuations),
                        page_number=cell.page_number,
                    )
                )

    # ---- path 2: records that open with a code, assembled with their wrapped continuations
    def starts(b: LayoutBlock) -> bool:
        if id(b) in paired_blocks:
            return False
        m = CODE_AT_START.match(b.text)
        return bool(m) and not _rejects(b.text, m)

    def may_continue(b: LayoutBlock) -> bool:
        # A wrapped remainder never begins with its own code and is never a heading.
        return b.block_type is not BlockType.HEADING and not CODE_AT_START.match(b.text)

    records = assemble_records(blocks, starts, allow_continuation=may_continue)
    lane_counts: dict[tuple[int, object, object], int] = {}
    for r in records:
        h = r.head
        lane = (h.page_number, h.table_id, h.cell_id if h.cell_id is not None else h.column_id)
        lane_counts[lane] = lane_counts.get(lane, 0) + 1

    for r in records:
        head = r.head
        m = CODE_AT_START.match(r.text)
        if not m:
            continue
        reason: str | None = None
        evidence = list(head.structural_evidence)
        lane = (head.page_number, head.table_id, head.cell_id if head.cell_id is not None else head.column_id)
        heading = _heading_governs(head, headings)
        if head.block_type is BlockType.TABLE_CELL:
            reason = "TABLE_CELL_SERIES" if lane_counts.get(lane, 0) >= MIN_SERIES else None
            if reason:
                evidence.append(f"lane_records:{lane_counts[lane]}")
        if reason is None and lane_counts.get(lane, 0) >= MIN_SERIES:
            reason = "COLUMN_SERIES"
            evidence.append(f"lane_records:{lane_counts[lane]}")
        if reason is None and heading is not None:
            reason = "CODE_TABLE_HEADING"
            evidence.append(f"heading:{heading.text[:60]!r}")
        if reason is None:
            continue
        meaning = _clean_meaning(m["meaning"])
        if not _valid_meaning(meaning):
            continue
        system, code = normalize_code(m["code"])
        key = (head.locator, code, meaning.lower())
        if key in seen:
            continue
        seen.add(key)
        if r.continuation_count:
            evidence.append(f"continuations:{r.continuation_count}")
        out.append(
            CodeCandidate(
                code_system=system,
                code=code,
                meaning=meaning,
                raw=m.group(0).strip()[:200],
                locator=head.locator,
                excerpt=r.excerpt,
                structural_reason=reason,
                evidence=tuple(evidence) + tuple(r.evidence),
                continuation_lines=r.continuation_count,
                page_number=head.page_number,
            )
        )
    out.sort(key=lambda c: (c.page_number or 0, c.locator, c.code))
    return out


def parse_code_blocks(blocks: list[TextBlock]) -> list[CodeCandidate]:
    """Legacy entry point: flattened text with no geometry.

    Retained so existing scripts keep working. Text-only input can still satisfy
    ``COLUMN_SERIES`` when several consecutive lines each open with a code, which is what a
    plain-text code list looks like; a single isolated line cannot.
    """
    return parse_codes(_layout_from_text_blocks(blocks))


def _layout_from_text_blocks(blocks: list[TextBlock]) -> DocumentLayout:
    from radiocorpus.layout.model import PageLayout

    lbs: list[LayoutBlock] = []
    order = 0
    for tb in blocks:
        for line in tb.text.splitlines():
            if not line.strip():
                continue
            lbs.append(
                LayoutBlock(
                    text=line.strip(),
                    page_number=1,
                    reading_order=order,
                    block_type=BlockType.UNKNOWN,
                    backend="text",
                    structural_evidence=("text_only",),
                    legacy_locator=tb.locator,
                )
            )
            order += 1
    doc = DocumentLayout(backend="text")
    doc.pages.append(PageLayout(1, None, None, tuple(lbs), 1, None, "text", ()))
    return doc


__all__ = [
    "CodeCandidate",
    "layout_from_text",
    "normalize_code",
    "parse_code_blocks",
    "parse_codes",
]
