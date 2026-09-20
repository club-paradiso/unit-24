"""Assemble multi-line records out of layout blocks.

A table cell that wraps onto a second visual line is the single most damaging layout failure
in the audited corpus: the wrapped remainder lands on the next row and is read as part of a
neighbouring code's meaning. Assembly is generic here — the caller supplies the predicate
that says "this line opens a new record" — so no document-format knowledge leaks into the
layout layer.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from radiocorpus.layout.model import BBox, BlockType, LayoutBlock

MAX_CONTINUATION_GAP_FACTOR = 2.2  # multiples of line height before a gap breaks the record


@dataclass(slots=True)
class Record:
    """One logical entry assembled from one or more layout blocks in a single column."""

    blocks: list[LayoutBlock]
    continuation_count: int = 0
    evidence: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(b.text.strip() for b in self.blocks if b.text.strip())

    @property
    def head(self) -> LayoutBlock:
        return self.blocks[0]

    @property
    def locator(self) -> str:
        return self.head.locator

    @property
    def bbox(self) -> BBox | None:
        boxes = [b.bbox for b in self.blocks if b.bbox]
        if not boxes:
            return None
        out = boxes[0]
        for b in boxes[1:]:
            out = out.merge(b)
        return out

    @property
    def excerpt(self) -> str:
        return self.text[:300]


def _lane(block: LayoutBlock) -> tuple[int, object, object]:
    """Blocks only ever merge within one page and one column/cell lane."""
    return (block.page_number, block.table_id, block.cell_id if block.cell_id is not None else block.column_id)


def assemble_records(
    blocks: list[LayoutBlock],
    starts_record: Callable[[LayoutBlock], bool],
    *,
    allow_continuation: Callable[[LayoutBlock], bool] | None = None,
) -> list[Record]:
    """Group blocks into records within each column lane.

    A block that does not open a record continues the record above it when the two are
    vertically adjacent in the same lane. Text with no geometry never continues anything:
    without coordinates we cannot show the two lines were neighbours.
    """
    lanes: dict[tuple[int, object, object], list[LayoutBlock]] = defaultdict(list)
    for b in blocks:
        if b.excluded:
            continue
        lanes[_lane(b)].append(b)

    records: list[Record] = []
    for lane_blocks in lanes.values():
        ordered = sorted(lane_blocks, key=lambda b: b.reading_order)
        current: Record | None = None
        for b in ordered:
            if starts_record(b):
                current = Record(blocks=[b], evidence=[f"record_start:{b.block_type}"])
                records.append(current)
                continue
            if current is None:
                continue
            if allow_continuation is not None and not allow_continuation(b):
                current = None
                continue
            prev = current.blocks[-1]
            if prev.bbox is None or b.bbox is None:
                # No geometry: refuse to merge rather than guess adjacency.
                current = None
                continue
            gap = b.bbox.y0 - prev.bbox.y1
            line_h = max(prev.bbox.height, b.bbox.height, 1.0)
            if gap > line_h * MAX_CONTINUATION_GAP_FACTOR or gap < -line_h:
                current = None
                continue
            current.blocks.append(b)
            current.continuation_count += 1
            current.evidence.append(f"continuation:same_lane_gap={gap:.1f}")
    records.sort(key=lambda r: r.head.reading_order)
    return records


def is_table_cell(block: LayoutBlock) -> bool:
    return block.block_type is BlockType.TABLE_CELL
