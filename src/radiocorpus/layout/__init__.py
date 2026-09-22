"""Layout-aware document representation.

The old abstraction was ``TextBlock(locator, text)``: a flattened page of text with no
geometry. That loses exactly the information needed to read a multi-column code table, to
tell a section heading from a phonetic pair, or to know that a sentence continues onto the
next page. This package replaces it with a position-aware representation and keeps the
flattened path available as an explicitly-labelled fallback.

Nothing here decides what a fact means. It decides *where text is* and *what shape it has*,
and records the evidence for each structural claim so a reviewer can check it.
"""

from radiocorpus.layout.model import (  # noqa: F401
    LAYOUT_VERSION,
    BBox,
    BlockType,
    DocumentLayout,
    LayoutBlock,
    PageLayout,
)

__all__ = ["LAYOUT_VERSION", "BBox", "BlockType", "DocumentLayout", "LayoutBlock", "PageLayout"]
