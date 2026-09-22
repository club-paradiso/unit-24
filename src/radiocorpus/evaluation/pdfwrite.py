"""A minimal PDF writer used to build synthetic documents with exact geometry.

This exists so that evaluation material can be generated with known coordinates rather than
scraped from a third-party file. It is deliberately tiny: text runs placed at absolute
positions, and — for the scanned-page gate — a page whose only content is an image.

The text path is byte-for-byte the writer that produced the committed layout fixtures; a test
asserts the fixtures still regenerate identically.
"""

from __future__ import annotations

import zlib

CHAR_W = 0.50  # Helvetica width factor, good enough to wrap synthetic text realistically


def pdf(pages: list[list[tuple]], width: int = 612, height: int = 792) -> bytes:
    """Write a PDF placing each run at an exact (x, y-from-bottom) coordinate."""
    objs: list[bytes] = []

    def add(b: bytes) -> int:
        objs.append(b)
        return len(objs)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    fontb = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    page_ids: list[int] = []
    pages_obj_index = len(objs) + 1 + 2 * len(pages)
    for runs in pages:
        parts = []
        for run in runs:
            x, y, size, text = run[0], run[1], run[2], run[3]
            key = "F2" if (len(run) > 4 and run[4] == "bold") else "F1"
            esc = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            parts.append(f"BT /{key} {size} Tf {x} {y} Td ({esc}) Tj ET")
        stream = " ".join(parts).encode("latin-1", "replace")
        contents = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_ids.append(
            add(
                f"<< /Type /Page /Parent {pages_obj_index} 0 R /MediaBox [0 0 {width} {height}] "
                f"/Contents {contents} 0 R /Resources << /Font << /F1 {font} 0 R /F2 {fontb} 0 R >> >> >>".encode()
            )
        )
    pages_obj = add(("<< /Type /Pages /Kids [" + " ".join(f"{p} 0 R" for p in page_ids) + f"] /Count {len(page_ids)} >>").encode())
    assert pages_obj == pages_obj_index
    catalog = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())
    return _assemble(objs, catalog)


def wrap(text: str, size: float, width: float) -> list[str]:
    limit = max(4, int(width / (size * CHAR_W)))
    lines: list[str] = []
    cur = ""
    for word in text.split():
        nxt = (cur + " " + word).strip()
        if len(nxt) <= limit:
            cur = nxt
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_width(text: str, size: float, *, bold: bool = False) -> float:
    """Exact width of a Helvetica run, from the font's own metrics.

    The approximate character width used by the original fixtures is good enough for those
    hand-checked pages, but a generated corpus needs text that provably stays inside its
    column: otherwise the generator emits a layout no real document has, and the parser is
    then scored against geometry that was never valid.
    """
    from pdfminer.fontmetrics import FONT_METRICS

    widths = FONT_METRICS["Helvetica-Bold" if bold else "Helvetica"][1]
    return sum(widths.get(ch, 556) for ch in text) * size / 1000.0


def wrap_exact(text: str, size: float, width: float, *, bold: bool = False) -> list[str]:
    """Greedy wrap using measured glyph widths, so no line can overflow ``width``."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        nxt = f"{cur} {word}".strip()
        if cur and text_width(nxt, size, bold=bold) > width:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    return lines


def scanned_pdf(*, width: int = 612, height: int = 792, caption: str | None = None, pixels: int = 8) -> bytes:
    """A page whose content is an image, as a scan is.

    ``caption`` optionally adds a short text run, so the fail-closed threshold can be probed
    from both sides: below ``MIN_NATIVE_CHARS`` the page must be refused, above it the page is
    ordinary native text that happens to carry an image.
    """
    objs: list[bytes] = []

    def add(b: bytes) -> int:
        objs.append(b)
        return len(objs)

    # A grey raster. The bytes are irrelevant to the gate; its presence is what matters.
    raw = bytes((i * 37) % 256 for i in range(pixels * pixels))
    data = zlib.compress(raw)
    image = add(
        f"<< /Type /XObject /Subtype /Image /Width {pixels} /Height {pixels} /ColorSpace /DeviceGray "
        f"/BitsPerComponent 8 /Filter /FlateDecode /Length {len(data)} >>".encode()
        + b"\nstream\n"
        + data
        + b"\nendstream"
    )
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    body = f"q {width} 0 0 {height} 0 0 cm /Im0 Do Q"
    if caption:
        esc = caption.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        body += f" BT /F1 9 Tf 40 {height - 40} Td ({esc}) Tj ET"
    stream = body.encode("latin-1", "replace")
    contents = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    pages_obj_index = len(objs) + 2
    page = add(
        f"<< /Type /Page /Parent {pages_obj_index} 0 R /MediaBox [0 0 {width} {height}] "
        f"/Contents {contents} 0 R /Resources << /XObject << /Im0 {image} 0 R >> "
        f"/Font << /F1 {font} 0 R >> >> >>".encode()
    )
    pages_obj = add(f"<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>".encode())
    assert pages_obj == pages_obj_index
    catalog = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())
    return _assemble(objs, catalog)


def empty_pdf(*, pages: int = 1, width: int = 612, height: int = 792) -> bytes:
    """A PDF with pages but no text and no images.

    Real documents look like this when their text is drawn as vector outlines. Nothing can be
    extracted and the scanned-page gate cannot fire, because there is no image to point at, so
    the document has to announce that it yielded nothing rather than pass silently.
    """
    objs: list[bytes] = []

    def add(b: bytes) -> int:
        objs.append(b)
        return len(objs)

    page_ids: list[int] = []
    pages_obj_index = len(objs) + 1 + 2 * pages
    for _ in range(pages):
        stream = b"0 0 m 10 10 l S"  # a drawn line: ink, but no text and no image
        contents = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_ids.append(
            add(
                f"<< /Type /Page /Parent {pages_obj_index} 0 R /MediaBox [0 0 {width} {height}] "
                f"/Contents {contents} 0 R /Resources << >> >>".encode()
            )
        )
    pages_obj = add(("<< /Type /Pages /Kids [" + " ".join(f"{p} 0 R" for p in page_ids) + f"] /Count {pages} >>").encode())
    assert pages_obj == pages_obj_index
    catalog = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())
    return _assemble(objs, catalog)


def _assemble(objs: list[bytes], catalog: int) -> bytes:
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


__all__ = ["CHAR_W", "empty_pdf", "pdf", "scanned_pdf", "text_width", "wrap", "wrap_exact"]
