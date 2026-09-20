"""Layout cache keyed by document hash AND layout version.

Layout extraction is the slow part of the pipeline. Caching it is safe only while the cache
key pins the code that produced the entry: a layout-algorithm change must invalidate every
entry, never silently reuse output from an older segmentation.
"""

from __future__ import annotations

import json
from pathlib import Path

from radiocorpus.layout.model import (
    LAYOUT_VERSION,
    BBox,
    BlockType,
    DocumentLayout,
    LayoutBlock,
    PageLayout,
    layout_code_fingerprint,
)

CACHE_SCHEMA = "2"


def cache_key(document_hash: str, *, layout_version: str = LAYOUT_VERSION, fingerprint: str | None = None) -> str:
    digest = document_hash.split(":", 1)[-1]
    fp = fingerprint or layout_code_fingerprint()
    return f"{digest}.{layout_version}.{fp}.v{CACHE_SCHEMA}.json"


def cache_path(root: Path, document_hash: str, *, layout_version: str = LAYOUT_VERSION, fingerprint: str | None = None) -> Path:
    return root / cache_key(document_hash, layout_version=layout_version, fingerprint=fingerprint)


def save(layout: DocumentLayout, root: Path, document_hash: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    fingerprint = layout_code_fingerprint()
    path = cache_path(root, document_hash, layout_version=layout.layout_version, fingerprint=fingerprint)
    payload = layout.to_dict()
    payload["_cache_schema"] = CACHE_SCHEMA
    payload["_document_hash"] = document_hash
    payload["_layout_code_fingerprint"] = fingerprint
    path.write_text(json.dumps(payload, sort_keys=True))
    return path


def load(root: Path, document_hash: str, *, layout_version: str = LAYOUT_VERSION) -> DocumentLayout | None:
    fingerprint = layout_code_fingerprint()
    path = cache_path(root, document_hash, layout_version=layout_version, fingerprint=fingerprint)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    if payload.get("_cache_schema") != CACHE_SCHEMA or payload.get("layout_version") != layout_version:
        return None
    if payload.get("_document_hash") != document_hash:
        return None
    if payload.get("_layout_code_fingerprint") != fingerprint:
        return None
    return _from_dict(payload)


def _from_dict(payload: dict) -> DocumentLayout:
    doc = DocumentLayout(
        backend=payload.get("backend", "unknown"),
        layout_version=payload.get("layout_version", LAYOUT_VERSION),
        document_hash=payload.get("document_hash"),
        content_type=payload.get("content_type"),
        warnings=list(payload.get("warnings", [])),
    )
    for p in payload.get("pages", []):
        blocks = []
        for b in p.get("blocks", []):
            bb = b.get("bbox")
            blocks.append(
                LayoutBlock(
                    text=b["text"],
                    page_number=b["page_number"],
                    reading_order=b["reading_order"],
                    block_type=BlockType(b["block_type"]),
                    bbox=BBox(bb["x0"], bb["y0"], bb["x1"], bb["y1"]) if bb else None,
                    printed_page_number=b.get("printed_page_number"),
                    column_id=b.get("column_id"),
                    table_id=b.get("table_id"),
                    row_id=b.get("row_id"),
                    cell_id=b.get("cell_id"),
                    backend=b.get("backend", "unknown"),
                    structural_evidence=tuple(b.get("structural_evidence", ())),
                    excluded=bool(b.get("excluded")),
                    exclusion_reason=b.get("exclusion_reason"),
                    font_size=b.get("font_size"),
                    bold=b.get("bold"),
                    section_path=tuple(b.get("section_path", ())),
                )
            )
        doc.pages.append(
            PageLayout(
                page_number=p["page_number"],
                width=p.get("width"),
                height=p.get("height"),
                blocks=tuple(blocks),
                column_count=p.get("column_count", 1),
                printed_page_number=p.get("printed_page_number"),
                text_extraction_method=p.get("text_extraction_method", "unknown"),
                notes=tuple(p.get("notes", ())),
            )
        )
    return doc
