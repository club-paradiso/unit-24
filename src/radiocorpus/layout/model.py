"""Layout data model and stable locators.

Coordinates follow the pdfplumber convention: the origin is the TOP-left of the page,
``y0`` is the distance from the top edge, and ``y1`` is the bottom of the box. Larger y is
further down the page. HTML and text backends leave ``bbox`` as ``None`` — absence of
geometry is a fact about the backend, never a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

# Declared version of the layout contract. It is deliberately NOT the whole cache key: a
# reviewer can forget to bump it, and a stale cache then serves layout produced by code that
# no longer exists. :func:`layout_code_fingerprint` closes that gap by hashing the source of
# the modules that actually produce layout.
LAYOUT_VERSION = "layout-2"


def layout_code_fingerprint() -> str:
    """Digest of every module that can change emitted layout.

    Any edit to the layout package changes this value, which invalidates cached layout
    automatically. This is what makes the cache safe to keep across code changes.
    """
    import hashlib
    from pathlib import Path

    here = Path(__file__).parent
    digest = hashlib.sha256()
    for name in sorted(("model.py", "segment.py", "backends.py", "records.py")):
        path = here / name
        if path.exists():
            digest.update(name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


class BlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    HEADER = "header"
    FOOTER = "footer"
    LIST_ITEM = "list_item"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BBox:
    x0: float
    y0: float  # distance from page top
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    def merge(self, other: BBox) -> BBox:
        return BBox(min(self.x0, other.x0), min(self.y0, other.y0), max(self.x1, other.x1), max(self.y1, other.y1))

    def as_locator(self) -> str:
        return f"({self.x0:.1f},{self.y0:.1f},{self.x1:.1f},{self.y1:.1f})"

    def to_dict(self) -> dict[str, float]:
        # Full precision: locators are derived from these numbers, so a rounded round-trip
        # would silently change a fact's address.
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}


@dataclass(frozen=True, slots=True)
class LayoutBlock:
    """One addressable region of a document.

    ``structural_evidence`` records why the block carries the type, column and table
    identity it claims. A claim with no evidence entry is a bug, not a default.
    """

    text: str
    page_number: int  # physical page, 1-based
    reading_order: int
    block_type: BlockType = BlockType.UNKNOWN
    bbox: BBox | None = None
    printed_page_number: str | None = None
    column_id: int | None = None
    table_id: int | None = None
    row_id: int | None = None
    cell_id: int | None = None
    backend: str = "unknown"
    structural_evidence: tuple[str, ...] = ()
    excluded: bool = False  # retained for audit; parsers skip it
    exclusion_reason: str | None = None
    font_size: float | None = None
    bold: bool | None = None
    section_path: tuple[str, ...] = ()  # enclosing headings, outermost first
    legacy_locator: str | None = None  # e.g. "html:table[1]>tr[3]" when the backend is not geometric

    @property
    def locator(self) -> str:
        """Stable, reconstructable address.

        Geometry-bearing blocks include the rounded bbox, so the address survives a change in
        block indexing. Non-geometric backends keep their structural path.
        """
        if self.legacy_locator is not None:
            return self.legacy_locator
        parts = [f"p.{self.page_number}"]
        if self.table_id is not None:
            parts.append(f"tbl[{self.table_id}]")
            if self.row_id is not None:
                parts.append(f"row[{self.row_id}]")
            if self.cell_id is not None:
                parts.append(f"col[{self.cell_id}]")
        elif self.column_id is not None:
            parts.append(f"col[{self.column_id}]")
        loc = ":".join(parts)
        if self.bbox is not None:
            loc = f"{loc}@{self.bbox.as_locator()}"
        return loc

    @property
    def page_locator(self) -> str:
        return f"p.{self.page_number}"

    def with_text(self, text: str, *, evidence: str | None = None) -> LayoutBlock:
        ev = self.structural_evidence + ((evidence,) if evidence else ())
        return replace(self, text=text, structural_evidence=ev)

    def exclude(self, reason: str, block_type: BlockType | None = None) -> LayoutBlock:
        return replace(
            self,
            excluded=True,
            exclusion_reason=reason,
            block_type=block_type or self.block_type,
            structural_evidence=self.structural_evidence + (f"excluded:{reason}",),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "locator": self.locator,
            "text": self.text,
            "page_number": self.page_number,
            "printed_page_number": self.printed_page_number,
            "reading_order": self.reading_order,
            "block_type": str(self.block_type),
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "column_id": self.column_id,
            "table_id": self.table_id,
            "row_id": self.row_id,
            "cell_id": self.cell_id,
            "backend": self.backend,
            "structural_evidence": list(self.structural_evidence),
            "excluded": self.excluded,
            "exclusion_reason": self.exclusion_reason,
            "font_size": self.font_size,
            "bold": self.bold,
            "section_path": list(self.section_path),
        }


@dataclass(frozen=True, slots=True)
class PageLayout:
    page_number: int
    width: float | None
    height: float | None
    blocks: tuple[LayoutBlock, ...]
    column_count: int = 1
    printed_page_number: str | None = None
    text_extraction_method: str = "unknown"  # native_pdf_text | ocr | html | text
    notes: tuple[str, ...] = ()

    def included(self) -> tuple[LayoutBlock, ...]:
        return tuple(b for b in self.blocks if not b.excluded)


@dataclass
class DocumentLayout:
    pages: list[PageLayout] = field(default_factory=list)
    backend: str = "unknown"
    layout_version: str = LAYOUT_VERSION
    document_hash: str | None = None
    content_type: str | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def blocks(self) -> list[LayoutBlock]:
        """Every block in reading order, including excluded ones (audit view)."""
        return [b for p in self.pages for b in p.blocks]

    def included_blocks(self) -> list[LayoutBlock]:
        """Blocks parsers may read: headers, footers and page furniture are dropped here."""
        return [b for p in self.pages for b in p.blocks if not b.excluded]

    @property
    def text_extraction_methods(self) -> set[str]:
        return {p.text_extraction_method for p in self.pages}

    def page(self, n: int) -> PageLayout | None:
        for p in self.pages:
            if p.page_number == n:
                return p
        return None

    def full_text(self) -> str:
        return "\n".join(b.text for b in self.included_blocks())

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "layout_version": self.layout_version,
            "document_hash": self.document_hash,
            "content_type": self.content_type,
            "warnings": list(self.warnings),
            "pages": [
                {
                    "page_number": p.page_number,
                    "width": p.width,
                    "height": p.height,
                    "column_count": p.column_count,
                    "printed_page_number": p.printed_page_number,
                    "text_extraction_method": p.text_extraction_method,
                    "notes": list(p.notes),
                    "blocks": [b.to_dict() for b in p.blocks],
                }
                for p in self.pages
            ],
        }


def layout_from_text(text: str, *, locator: str = "p.1", page_number: int = 1, backend: str = "text") -> DocumentLayout:
    """Wrap flattened text as a single-block layout.

    Used by the replay harness and by the legacy text path. Blocks produced this way carry
    ``structural_evidence=("text_only",)`` so a parser can tell that no geometry was
    available and refuse claims that require structural support.
    """
    block = LayoutBlock(
        text=text,
        page_number=page_number,
        reading_order=0,
        block_type=BlockType.UNKNOWN,
        backend=backend,
        structural_evidence=("text_only",),
        legacy_locator=locator,
    )
    page = PageLayout(page_number=page_number, width=None, height=None, blocks=(block,), text_extraction_method=backend)
    return DocumentLayout(pages=[page], backend=backend)
