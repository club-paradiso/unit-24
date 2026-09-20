"""Conservative geometric segmentation.

Every routine here is deliberately timid: when the geometry does not clearly support a
structural claim, it returns the weaker answer. A document wrongly declared single-column
loses precision in one table; a document wrongly declared multi-column corrupts every line
on the page. The asymmetry is intentional.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from radiocorpus.layout.model import BBox

# ---------------------------------------------------------------- words and lines


@dataclass(frozen=True, slots=True)
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float | None = None
    fontname: str | None = None

    @property
    def bold(self) -> bool:
        return bool(self.fontname and ("bold" in self.fontname.lower() or "black" in self.fontname.lower()))


@dataclass(slots=True)
class Line:
    words: list[Word]
    column_id: int | None = None

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def bbox(self) -> BBox:
        return BBox(
            min(w.x0 for w in self.words),
            min(w.top for w in self.words),
            max(w.x1 for w in self.words),
            max(w.bottom for w in self.words),
        )

    @property
    def top(self) -> float:
        return min(w.top for w in self.words)

    @property
    def bottom(self) -> float:
        return max(w.bottom for w in self.words)

    @property
    def size(self) -> float | None:
        sizes = [w.size for w in self.words if w.size]
        return statistics.median(sizes) if sizes else None

    @property
    def bold(self) -> bool:
        return bool(self.words) and all(w.bold for w in self.words)


def cluster_lines(words: list[Word], *, tol: float = 2.5) -> list[Line]:
    """Group words into visual lines by vertical position, then order left to right."""
    if not words:
        return []
    heights = [w.bottom - w.top for w in words if w.bottom > w.top]
    band = max(tol, (statistics.median(heights) * 0.6) if heights else tol)
    lines: list[list[Word]] = []
    for w in sorted(words, key=lambda w: (w.top, w.x0)):
        placed = False
        for group in reversed(lines):
            ref = group[0]
            # Same line when the vertical centres are within a fraction of the glyph height.
            if abs(((w.top + w.bottom) / 2) - ((ref.top + ref.bottom) / 2)) <= band:
                group.append(w)
                placed = True
                break
        if not placed:
            lines.append([w])
    out = [Line(sorted(g, key=lambda w: w.x0)) for g in lines]
    return sorted(out, key=lambda ln: (ln.top, ln.bbox.x0))


# ---------------------------------------------------------------- columns


@dataclass(slots=True)
class ColumnLayout:
    bounds: list[tuple[float, float]] = field(default_factory=list)
    gutters: list[tuple[float, float]] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return max(1, len(self.bounds))

    def column_of(self, x_center: float) -> int:
        if not self.bounds:
            return 0
        for i, (a, b) in enumerate(self.bounds):
            if a <= x_center <= b:
                return i
        # Outside every band: attach to the nearest band rather than inventing a column.
        return min(range(len(self.bounds)), key=lambda i: min(abs(x_center - self.bounds[i][0]), abs(x_center - self.bounds[i][1])))


MIN_GUTTER_PT = 12.0
GUTTER_OCCUPANCY_TOLERANCE = 0.15  # share of rows allowed to cross a gutter (titles, spanning notes)
MIN_COLUMN_ROWS = 3
MIN_COLUMN_WIDTH_PT = 40.0


def detect_columns(
    lines: list[Line],
    *,
    page_width: float | None,
    min_gutter: float = MIN_GUTTER_PT,
    bin_size: float = 2.0,
) -> ColumnLayout:
    """Find vertical gutters that persist down the page.

    A gutter only counts when it is wide, when text sits on both sides of it, and when it is
    respected by most text rows. A single wide-margin paragraph therefore cannot masquerade
    as a column break.
    """
    layout = ColumnLayout()
    body = [ln for ln in lines if ln.words]
    if len(body) < MIN_COLUMN_ROWS or not page_width:
        layout.evidence.append("single_column:insufficient_rows" if not page_width else "single_column:too_few_lines")
        return layout

    x_min = min(ln.bbox.x0 for ln in body)
    x_max = max(ln.bbox.x1 for ln in body)
    if x_max - x_min < MIN_COLUMN_WIDTH_PT * 2:
        layout.evidence.append("single_column:narrow_text_area")
        return layout

    nbins = max(1, int((x_max - x_min) / bin_size) + 1)
    # Occupancy counts LINES, not words, so one wide title cannot outvote the body.
    occupied = [0] * nbins

    def bin_of(x: float) -> int:
        return min(nbins - 1, max(0, int((x - x_min) / bin_size)))

    for ln in body:
        covered: set[int] = set()
        for w in ln.words:
            covered.update(range(bin_of(w.x0), bin_of(w.x1) + 1))
        for b in covered:
            occupied[b] += 1

    # A gutter is a band that most rows leave empty. Requiring *total* emptiness would let a
    # single full-width title or a spanning note erase a real column break.
    tolerance = int(len(body) * GUTTER_OCCUPANCY_TOLERANCE)
    gaps: list[tuple[float, float]] = []
    i = 0
    while i < nbins:
        if occupied[i] <= tolerance:
            j = i
            while j < nbins and occupied[j] <= tolerance:
                j += 1
            start, end = x_min + i * bin_size, x_min + j * bin_size
            if i > 0 and j < nbins and (end - start) >= min_gutter:
                gaps.append((start, end))
            i = j
        else:
            i += 1
    if not gaps:
        layout.evidence.append("single_column:no_gutter")
        return layout

    # Candidate bands between gutters.
    edges = [x_min] + [g[0] for g in gaps] + [x_max]
    starts = [x_min] + [g[1] for g in gaps]
    bands = [(s, e) for s, e in zip(starts, edges[1:], strict=False) if e - s >= MIN_COLUMN_WIDTH_PT]
    if len(bands) < 2:
        layout.evidence.append("single_column:no_band_pair")
        return layout

    # A band only counts when several rows put text in it.
    rows_with = Counter()
    for ln in body:
        for bi, (a, b) in enumerate(bands):
            if any(a <= (w.x0 + w.x1) / 2 <= b for w in ln.words):
                rows_with[bi] += 1
    live = [bi for bi in range(len(bands)) if rows_with[bi] >= MIN_COLUMN_ROWS]
    if len(live) < 2:
        layout.evidence.append("single_column:bands_not_populated")
        return layout

    # Reject when most rows span a gutter: that means the gutter is an artefact of ragged text.
    spanning = 0
    for ln in body:
        touched = {bi for bi in live if any(bands[bi][0] <= (w.x0 + w.x1) / 2 <= bands[bi][1] for w in ln.words)}
        if len(touched) > 1 and _has_wide_intra_line_gap(ln, gaps) is False:
            spanning += 1
    if spanning > len(body) * 0.5:
        layout.evidence.append("single_column:rows_span_gutters")
        return layout

    layout.bounds = [bands[bi] for bi in live]
    layout.gutters = list(gaps)
    layout.evidence.append(f"columns:{len(layout.bounds)}_bands_gutters={len(gaps)}_rows>={MIN_COLUMN_ROWS}")
    return layout


def spans_columns(line: Line, columns: ColumnLayout) -> bool:
    """True when one visual line genuinely runs across a gutter as continuous text.

    A banner heading or a full-width note must be kept whole; splitting it by column would
    shred a sentence into fragments that parsers would then read out of order.
    """
    if columns.count <= 1:
        return False
    touched = {columns.column_of((w.x0 + w.x1) / 2) for w in line.words}
    if len(touched) < 2:
        return False
    return not _has_wide_intra_line_gap(line, columns.gutters)


def _has_wide_intra_line_gap(line: Line, gaps: list[tuple[float, float]]) -> bool:
    """True when the line's own word spacing contains one of the page gutters."""
    ws = sorted(line.words, key=lambda w: w.x0)
    for a, b in zip(ws, ws[1:], strict=False):
        gap0, gap1 = a.x1, b.x0
        for g0, g1 in gaps:
            if gap0 <= g0 and gap1 >= g1:
                return True
    return False


def split_line_by_columns(line: Line, columns: ColumnLayout) -> dict[int, Line]:
    """Cut one visual line into per-column fragments."""
    if columns.count <= 1:
        return {0: line}
    buckets: dict[int, list[Word]] = defaultdict(list)
    for w in line.words:
        buckets[columns.column_of((w.x0 + w.x1) / 2)].append(w)
    return {c: Line(sorted(ws, key=lambda w: w.x0), column_id=c) for c, ws in sorted(buckets.items()) if ws}


# ---------------------------------------------------------------- page furniture

_DIGITS = re.compile(r"\d+")
_PAGE_NUM = re.compile(r"^\s*(?:page\s*)?(\d{1,4})(?:\s*(?:of|/)\s*\d{1,4})?\s*$", re.I)
_PAGE_NUM_INLINE = re.compile(r"\bpage\s+(\d{1,4})\s+of\s+\d{1,4}\b", re.I)


def furniture_signature(text: str) -> str:
    """Normalise a line so that a page number or date does not defeat repetition matching."""
    return _DIGITS.sub("#", " ".join(text.split())).strip().lower()


FURNITURE_SHAPE = re.compile(
    r"^\s*(?:page\s*)?\d{1,4}\s*(?:of|/)\s*\d{1,4}\s*$|^\s*\d{1,4}\s*$|"
    r"\b(?:rev\.?|revision|form|directive|issued|effective|updated|page)\b",
    re.I,
)


def detect_repeated_furniture(
    page_lines: list[list[Line]],
    *,
    page_heights: list[float | None],
    band_fraction: float = 0.08,
    min_pages: int = 2,
) -> set[str]:
    """Signatures that repeat in the top or bottom band across pages.

    Two kinds of repetition count, and they are deliberately different in strictness:

    * **exact** repetition of the same text — a banner or a boilerplate footer;
    * **digit-normalised** repetition, but only for lines shaped like page furniture
      ("Page 3 of 11", a bare number, a revision stamp).

    Without the second restriction a section heading that merely numbers its parts would be
    normalised into a repeat and suppressed along with the real furniture.
    """
    if len(page_lines) < min_pages:
        return set()
    exact: dict[str, set[int]] = defaultdict(set)
    normalised: dict[str, set[int]] = defaultdict(set)
    shaped: set[str] = set()
    for pi, (lines, height) in enumerate(zip(page_lines, page_heights, strict=False)):
        if not height:
            continue
        top_band, bottom_band = height * band_fraction, height * (1 - band_fraction)
        for ln in lines:
            if not (ln.top <= top_band or ln.bottom >= bottom_band):
                continue
            text = " ".join(ln.text.split())
            if len(text) <= 2:
                continue
            sig = furniture_signature(text)
            exact[text.lower()].add(pi)
            normalised[sig].add(pi)
            if FURNITURE_SHAPE.search(text):
                shaped.add(sig)
    threshold = max(min_pages, int(len(page_lines) * 0.5))
    out = {furniture_signature(t) for t, pages in exact.items() if len(pages) >= threshold}
    out |= {sig for sig, pages in normalised.items() if len(pages) >= threshold and sig in shaped}
    return out


def extract_printed_page_number(lines: list[Line], *, height: float | None, band_fraction: float = 0.08) -> str | None:
    """The page number the document prints on itself, when it differs from the physical index."""
    if not height:
        return None
    top_band, bottom_band = height * band_fraction, height * (1 - band_fraction)
    for ln in lines:
        if not (ln.top <= top_band or ln.bottom >= bottom_band):
            continue
        t = ln.text.strip()
        m = _PAGE_NUM.match(t) or _PAGE_NUM_INLINE.search(t)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------- headings and list items

# "A.", "1.", "IV.", "a)", "2.3.1" — an enumerator introducing a clause, NOT a phonetic pair.
ENUMERATOR = re.compile(r"^\s*(?P<enum>(?:[A-Za-z]|\d{1,3}|[IVXivx]{1,5})\s*[.)]|\d+(?:\.\d+)+\.?)\s+(?=\S)")
_HEADING_WORDS = re.compile(r"^[A-Z0-9][A-Z0-9 ,.&/()'’-]{2,80}:?$")
_SENTENCE_END = re.compile(r"[.;:!?]\s*$")


def enumerator_of(text: str) -> str | None:
    m = ENUMERATOR.match(text)
    return m.group("enum").strip() if m else None


def strip_enumerator(text: str) -> str:
    m = ENUMERATOR.match(text)
    return text[m.end() :] if m else text


def looks_like_heading(line: Line, *, body_size: float | None, max_words: int = 12) -> tuple[bool, str]:
    """Heading detection from typography and shape, not from wording."""
    t = line.text.strip()
    if not t or len(t) > 120:
        return False, ""
    words = t.split()
    core = strip_enumerator(t).strip()
    if not core:
        return False, ""
    if line.bold and len(words) <= max_words:
        return True, "bold_short_line"
    if body_size and line.size and line.size >= body_size * 1.15 and len(words) <= max_words:
        return True, "larger_font"
    if core.isupper() and len(words) <= max_words and not _SENTENCE_END.search(core[:-1] if core.endswith(":") else core):
        return True, "all_caps_short_line"
    if enumerator_of(t) and _HEADING_WORDS.match(core) and len(words) <= max_words:
        return True, "enumerated_title_case"
    return False, ""


def body_font_size(lines: list[Line]) -> float | None:
    sizes = [ln.size for ln in lines if ln.size]
    return statistics.median(sizes) if sizes else None
