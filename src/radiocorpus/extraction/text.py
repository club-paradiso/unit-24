"""Content → text with locators. PDFs yield per-page text; HTML yields block text with a
simple element-path locator. Deterministic; no model involved."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextBlock:
    locator: str  # "p.3" | "html:body>table[1]>tr[7]" ...
    text: str
    method: str = "text"


class OCRRequired(ValueError):
    """Scanned pages are gated until an explicitly configured OCR backend is supplied."""


def pdf_blocks(data: bytes, *, ocr=None) -> list[TextBlock]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    out: list[TextBlock] = []
    for i, page in enumerate(reader.pages, 1):
        try:
            t = page.extract_text() or ""
        except Exception as e:  # pragma: no cover - pypdf edge cases
            raise ValueError(f"PDF page {i} extraction failed") from e
        method = "native_pdf_text"
        if len(t.strip()) < 20 and len(page.images) > 0:
            if ocr is None:
                raise OCRRequired(f"p.{i}: image content with fewer than 20 native-text characters")
            t = ocr.extract_page(data, i)
            method = "ocr"
            if not t.strip():
                raise OCRRequired(f"p.{i}: OCR produced no text")
        out.append(TextBlock(locator=f"p.{i}", text=t, method=method))
    return out


def html_blocks(data: bytes) -> list[TextBlock]:
    from selectolax.parser import HTMLParser

    tree = HTMLParser(data.decode("utf-8", errors="replace"))
    for tag in ("script", "style", "noscript"):
        for n in tree.css(tag):
            n.decompose()
    out: list[TextBlock] = []
    tables = tree.css("table")
    for ti, table in enumerate(tables, 1):
        for ri, row in enumerate(table.css("tr"), 1):
            cells = [c.text(separator=" ", strip=True) for c in row.css("th, td")]
            if any(cells):
                out.append(TextBlock(locator=f"html:table[{ti}]>tr[{ri}]", text=" | ".join(cells), method="html"))
        table.decompose()
    body = tree.body or tree.root
    if body is not None:
        for bi, node in enumerate(body.css("h1, h2, h3, h4, p, li, dt, dd, pre, div"), 1):
            if any(child.mem_id != node.mem_id for child in node.css("p, li, div, table")):
                continue  # only leaf-ish blocks
            t = node.text(separator=" ", strip=True)
            if t:
                out.append(TextBlock(locator=f"html:{node.tag}[{bi}]", text=t, method="html"))
    return out


def blocks_for(data: bytes, content_type: str | None) -> list[TextBlock]:
    ct = (content_type or "").lower()
    if "pdf" in ct or data[:5] == b"%PDF-":
        return pdf_blocks(data)
    if "html" in ct or b"<html" in data[:2000].lower():
        return html_blocks(data)
    text = data.decode("utf-8", errors="replace")
    return [TextBlock(locator=f"line.{i}", text=line) for i, line in enumerate(text.splitlines(), 1) if line.strip()]


def full_text(blocks: list[TextBlock]) -> str:
    return "\n".join(b.text for b in blocks)


_WS = re.compile(r"\s+")


def squash(s: str) -> str:
    return _WS.sub(" ", s).strip()
