"""Backends that turn bytes into a :class:`DocumentLayout`.

``pdfplumber`` (MIT, on pdfminer.six) supplies word coordinates, font name and size. It is
preferred over PyMuPDF because PyMuPDF is AGPL/commercial dual-licensed and this pipeline is
intended to feed a shipped product; see docs/decisions/0006.

The scanned-page contract from the previous sprint is preserved exactly: a PDF page with
almost no native text but with embedded images raises :class:`OCRRequired` unless an OCR
backend is explicitly supplied. Layout work never turns OCR on by itself.
"""

from __future__ import annotations

import io
import re
from collections import defaultdict
from dataclasses import replace

from radiocorpus.extraction.text import OCRRequired
from radiocorpus.layout.model import BlockType, DocumentLayout, LayoutBlock, PageLayout
from radiocorpus.layout.segment import (
    ColumnLayout,
    Line,
    Word,
    body_font_size,
    cluster_lines,
    detect_columns,
    detect_repeated_furniture,
    extract_printed_page_number,
    furniture_signature,
    looks_like_heading,
    spans_columns,
    split_line_by_columns,
)

PDF_BACKEND = "pdfplumber"
PDF_FALLBACK_BACKEND = "pypdf_text"
MIN_NATIVE_CHARS = 20
ROW_BAND_TOL = 3.0


def _words_from_pdfplumber_page(page) -> list[Word]:  # type: ignore[no-untyped-def]
    out: list[Word] = []
    for w in page.extract_words(use_text_flow=False, keep_blank_chars=False, extra_attrs=["fontname", "size"]):
        out.append(
            Word(
                text=w["text"],
                x0=float(w["x0"]),
                x1=float(w["x1"]),
                top=float(w["top"]),
                bottom=float(w["bottom"]),
                size=float(w["size"]) if w.get("size") is not None else None,
                fontname=w.get("fontname"),
            )
        )
    return out


def _row_bands(lines: list[Line], tol: float = ROW_BAND_TOL) -> dict[int, int]:
    """Map id(line) -> row index, clustering lines that share a horizontal band."""
    bands: list[float] = []
    assign: dict[int, int] = {}
    for ln in sorted(lines, key=lambda ln: ln.top):
        centre = (ln.top + ln.bottom) / 2
        for i, b in enumerate(bands):
            if abs(centre - b) <= tol:
                assign[id(ln)] = i
                break
        else:
            bands.append(centre)
            assign[id(ln)] = len(bands) - 1
    return assign


def _build_page(
    page_number: int,
    words: list[Word],
    width: float | None,
    height: float | None,
    *,
    furniture: set[str],
    method: str,
    backend: str,
    order_start: int,
) -> tuple[PageLayout, int]:
    lines = cluster_lines(words)
    order = order_start
    if not lines:
        return PageLayout(page_number, width, height, (), 1, None, method, ("empty_page",)), order

    columns: ColumnLayout = detect_columns(lines, page_width=width)
    printed = extract_printed_page_number(lines, height=height)
    body = body_font_size(lines)
    notes = tuple(columns.evidence)

    # Per-column fragments, remembering which visual row each came from.
    frags: list[tuple[int | None, int, Line]] = []  # (column_id, row_id, fragment)
    row_of = _row_bands(lines)
    spanning_rows: set[int] = set()
    for ln in lines:
        if spans_columns(ln, columns):
            # Full-width line: keep it intact rather than shredding it across columns.
            frags.append((None, row_of[id(ln)], ln))
            spanning_rows.add(row_of[id(ln)])
            continue
        for col, frag in split_line_by_columns(ln, columns).items():
            frags.append((col, row_of[id(ln)], frag))

    multi_col = columns.count > 1
    # A page is treated as tabular when several rows carry text in two or more columns.
    rows_by_cols: dict[int, set[int]] = defaultdict(set)
    for col, row, _ in frags:
        if col is not None:
            rows_by_cols[row].add(col)
    tabular = multi_col and sum(1 for cols in rows_by_cols.values() if len(cols) >= 2) >= 3
    table_id = 1 if tabular else None

    # Column-major reading order: never join the foot of one column to the head of the next.
    # Column-major, but a full-width line keeps its place in the page-level flow.
    frags.sort(key=lambda f: (-1 if f[0] is None else f[0], f[2].top, f[2].bbox.x0))

    blocks: list[LayoutBlock] = []
    for col, row, frag in frags:
        text = frag.text.strip()
        if not text:
            continue
        sig = furniture_signature(text)
        is_heading, heading_why = looks_like_heading(frag, body_size=body)
        evidence: list[str] = [f"backend:{backend}"]
        if multi_col and col is not None:
            evidence.append(f"column:{col}/{columns.count}")
        if tabular:
            evidence.append(f"table_row:{row}")
        full_width = col is None
        btype = BlockType.UNKNOWN
        if full_width:
            evidence.append("full_width:spans_columns")
        if tabular and not full_width:
            btype = BlockType.TABLE_CELL
            evidence.append("cell:column_aligned")
        elif is_heading:
            btype = BlockType.HEADING
            evidence.append(f"heading:{heading_why}")
        else:
            btype = BlockType.PARAGRAPH
        block = LayoutBlock(
            text=text,
            page_number=page_number,
            reading_order=order,
            block_type=btype,
            bbox=frag.bbox,
            printed_page_number=printed,
            column_id=col if (multi_col and col is not None) else None,
            table_id=table_id if (tabular and not full_width) else None,
            row_id=row if (tabular and not full_width) else None,
            cell_id=col if (tabular and not full_width) else None,
            backend=backend,
            structural_evidence=tuple(evidence),
            font_size=frag.size,
            bold=frag.bold,
        )
        if sig in furniture:
            band = "header" if height and frag.top <= height * 0.12 else "footer"
            block = block.exclude(f"repeated_{band}_across_pages", BlockType.HEADER if band == "header" else BlockType.FOOTER)
        elif printed is not None and text.strip() == printed:
            block = block.exclude("printed_page_number", BlockType.FOOTER)
        blocks.append(block)
        order += 1

    if not tabular:
        blocks = _merge_paragraph_lines(blocks)
    return PageLayout(page_number, width, height, tuple(blocks), columns.count, printed, method, notes), order


_SENTENCE_FINAL = re.compile(r"[.;:!?\u201d\"\)]\s*$")
_STARTS_NEW_ITEM = re.compile(r"^\s*(?:[A-Za-z]|\d{1,3}|[IVXivx]{1,5})\s*[.)]\s+|^\s*[\u2022\u00b7\u25aa\u2013-]\s+")
# Lines that open a list entry rather than continue a sentence. Merging these into a
# paragraph destroys the one-record-per-line structure that code and alphabet lists depend on.
_LIST_LINE = re.compile(
    r"^\s*(?:(?:10|11|12|13)\s?-\s?\d{1,3}[A-Za-z]?|(?:code|signal|status)\s?-?\s?\d{1,3}[A-Za-z]?)\b"
    r"|^\s*[A-Z]\s*[-\u2013:=|]?\s+[A-Z][A-Za-z]{2,13}\s*$",
    re.I,
)
# A revision or issue stamp sits above the body without ending in a full stop, so paragraph
# assembly used to glue it onto the first sentence beneath it. Everything downstream then
# inherited it: the rule text, the excerpt, and the subject of the rule, which came out as
# "Revision Date: 10-11-19 ... Units". A stamp is furniture, never the start of a sentence.
_STAMP_LINE = re.compile(
    r"^\s*(?:issued?|effective|revised?|revision|rev\.?|updated?|approved|amended|dated|supersedes?)\b"
    r"[^.]*?\d{1,4}[-/.]\d{1,2}[-/.]\d{2,4}\s*$",
    re.I,
)
PARAGRAPH_GAP_FACTOR = 1.8


def _merge_paragraph_lines(blocks: list[LayoutBlock]) -> list[LayoutBlock]:
    """Join consecutive body lines into paragraphs.

    Sentence-level rules are unreadable when a wrapped line is treated as a whole block: a
    rule split across two lines yields two fragments, neither of which is a sentence. Only
    adjacent, same-column, non-heading lines are joined, and only when the earlier line does
    not already close a sentence.
    """
    out: list[LayoutBlock] = []
    for b in blocks:
        if (
            out
            and not b.excluded
            and not out[-1].excluded
            and b.block_type is BlockType.PARAGRAPH
            and out[-1].block_type is BlockType.PARAGRAPH
            and b.column_id == out[-1].column_id
            and b.page_number == out[-1].page_number
            and b.bbox is not None
            and out[-1].bbox is not None
            and not _SENTENCE_FINAL.search(out[-1].text)
            and not _STARTS_NEW_ITEM.match(b.text)
            and not _LIST_LINE.match(b.text)
            and not _LIST_LINE.match(out[-1].text)
            and not _STAMP_LINE.match(out[-1].text)
            and not _STAMP_LINE.match(b.text)
        ):
            prev = out[-1]
            gap = b.bbox.y0 - prev.bbox.y1
            line_h = max(prev.bbox.height, b.bbox.height, 1.0)
            if -line_h <= gap <= line_h * PARAGRAPH_GAP_FACTOR:
                out[-1] = replace(
                    prev,
                    text=f"{prev.text} {b.text}".strip(),
                    bbox=prev.bbox.merge(b.bbox),
                    structural_evidence=prev.structural_evidence + ("paragraph_merge:wrapped_line",),
                )
                continue
        out.append(b)
    return out


def pdf_layout(data: bytes, *, ocr=None, document_hash: str | None = None) -> DocumentLayout:  # type: ignore[no-untyped-def]
    """Position-aware PDF layout, falling back to flattened native text when unavailable."""
    try:
        import pdfplumber
    except ImportError:  # pragma: no cover - dependency is declared
        return _pdf_text_fallback(data, ocr=ocr, document_hash=document_hash, reason="pdfplumber_not_installed")

    doc = DocumentLayout(backend=PDF_BACKEND, document_hash=document_hash, content_type="application/pdf")
    try:
        plumber = pdfplumber.open(io.BytesIO(data))
    except Exception as error:
        raise ValueError(f"PDF could not be opened for layout extraction: {error}") from error

    with plumber:
        page_words: list[list[Word]] = []
        dims: list[tuple[float | None, float | None]] = []
        methods: list[str] = []
        for i, page in enumerate(plumber.pages, 1):
            words = _words_from_pdfplumber_page(page)
            native_chars = sum(len(w.text) for w in words)
            method = "native_pdf_text"
            if native_chars < MIN_NATIVE_CHARS and page.images:
                if ocr is None:
                    raise OCRRequired(f"p.{i}: image content with fewer than {MIN_NATIVE_CHARS} native-text characters")
                text = ocr.extract_page(data, i)
                if not text.strip():
                    raise OCRRequired(f"p.{i}: OCR produced no text")
                # OCR returns text without geometry: represent it honestly as one block.
                words = [Word(text=text, x0=0.0, x1=float(page.width), top=0.0, bottom=float(page.height))]
                method = "ocr"
            page_words.append(words)
            dims.append((float(page.width), float(page.height)))
            methods.append(method)

        lines_per_page = [cluster_lines(ws) for ws in page_words]
        furniture = detect_repeated_furniture(lines_per_page, page_heights=[d[1] for d in dims])
        order = 0
        for i, (ws, (w, h), method) in enumerate(zip(page_words, dims, methods, strict=False), 1):
            page_layout, order = _build_page(
                i, ws, w, h, furniture=furniture, method=method, backend=PDF_BACKEND if method != "ocr" else "ocr", order_start=order
            )
            doc.pages.append(page_layout)
    if furniture:
        doc.warnings.append(f"suppressed_repeated_furniture:{len(furniture)}")
    if not doc.included_blocks():
        # A PDF whose pages carry no extractable text and no images yields nothing, and the
        # OCR gate never fires because there is no image to point at. Emitting nothing is the
        # right behaviour, but emitting nothing *silently* is indistinguishable from a document
        # that was read successfully and happened to be empty — which is exactly the shape of
        # an undetected scan. Found on a real government PDF whose text is drawn as vectors.
        doc.warnings.append(f"no_text_extracted:{len(doc.pages)}_pages_yielded_no_blocks")
    return doc


def _pdf_text_fallback(data: bytes, *, ocr=None, document_hash: str | None, reason: str) -> DocumentLayout:  # type: ignore[no-untyped-def]
    from radiocorpus.extraction.text import pdf_blocks

    doc = DocumentLayout(backend=PDF_FALLBACK_BACKEND, document_hash=document_hash, content_type="application/pdf")
    doc.warnings.append(f"layout_unavailable:{reason}")
    for order, tb in enumerate(pdf_blocks(data, ocr=ocr)):
        page_no = order + 1
        block = LayoutBlock(
            text=tb.text,
            page_number=page_no,
            reading_order=order,
            block_type=BlockType.UNKNOWN,
            backend=PDF_FALLBACK_BACKEND,
            structural_evidence=("text_only", f"fallback:{reason}"),
            legacy_locator=tb.locator,
        )
        doc.pages.append(PageLayout(page_no, None, None, (block,), 1, None, tb.method, (f"fallback:{reason}",)))
    return doc


def html_layout(data: bytes, *, document_hash: str | None = None) -> DocumentLayout:
    """HTML has no page geometry, but it has explicit structure: keep table identity."""
    from selectolax.parser import HTMLParser

    tree = HTMLParser(data.decode("utf-8", errors="replace"))
    for tag in ("script", "style", "noscript"):
        for n in tree.css(tag):
            n.decompose()
    doc = DocumentLayout(backend="html", document_hash=document_hash, content_type="text/html")
    blocks: list[LayoutBlock] = []
    order = 0
    for ti, table in enumerate(tree.css("table"), 1):
        for ri, row in enumerate(table.css("tr"), 1):
            cells = [c.text(separator=" ", strip=True) for c in row.css("th, td")]
            if not any(cells):
                continue
            for ci, cell in enumerate(cells, 1):
                if not cell.strip():
                    continue
                blocks.append(
                    LayoutBlock(
                        text=cell.strip(),
                        page_number=1,
                        reading_order=order,
                        block_type=BlockType.TABLE_CELL,
                        table_id=ti,
                        row_id=ri,
                        cell_id=ci,
                        column_id=ci - 1,
                        backend="html",
                        structural_evidence=("backend:html", "cell:html_table"),
                        legacy_locator=f"html:table[{ti}]>tr[{ri}]>cell[{ci}]",
                    )
                )
                order += 1
        table.decompose()
    body = tree.body or tree.root
    if body is not None:
        for bi, node in enumerate(body.css("h1, h2, h3, h4, h5, h6, p, li, dt, dd, pre, div"), 1):
            if any(child.mem_id != node.mem_id for child in node.css("p, li, div, table")):
                continue
            t = node.text(separator=" ", strip=True)
            if not t:
                continue
            if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                btype = BlockType.HEADING
            elif node.tag == "li":
                btype = BlockType.LIST_ITEM
            else:
                btype = BlockType.PARAGRAPH
            blocks.append(
                LayoutBlock(
                    text=t,
                    page_number=1,
                    reading_order=order,
                    block_type=btype,
                    backend="html",
                    structural_evidence=("backend:html", f"element:{node.tag}"),
                    legacy_locator=f"html:{node.tag}[{bi}]",
                )
            )
            order += 1
    doc.pages.append(PageLayout(1, None, None, tuple(blocks), 1, None, "html", ()))
    return doc


def text_layout(data: bytes, *, document_hash: str | None = None) -> DocumentLayout:
    text = data.decode("utf-8", errors="replace")
    blocks = [
        LayoutBlock(
            text=line,
            page_number=1,
            reading_order=i,
            block_type=BlockType.UNKNOWN,
            backend="text",
            structural_evidence=("text_only",),
            legacy_locator=f"line.{n}",
        )
        for i, (n, line) in enumerate((n, ln) for n, ln in enumerate(text.splitlines(), 1) if ln.strip())
    ]
    doc = DocumentLayout(backend="text", document_hash=document_hash, content_type=None)
    doc.pages.append(PageLayout(1, None, None, tuple(blocks), 1, None, "text", ()))
    return doc


def layout_for(data: bytes, content_type: str | None, *, ocr=None, document_hash: str | None = None) -> DocumentLayout:  # type: ignore[no-untyped-def]
    ct = (content_type or "").lower()
    if "pdf" in ct or data[:5] == b"%PDF-":
        return pdf_layout(data, ocr=ocr, document_hash=document_hash)
    if "html" in ct or b"<html" in data[:2000].lower():
        return html_layout(data, document_hash=document_hash)
    return text_layout(data, document_hash=document_hash)
