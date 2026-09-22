"""How much of the column detector's behaviour is the thresholds, and how much is the page?

The gutter width, the share of rows allowed to cross a gutter and the number of rows a band
must carry were all chosen against a single adversarial layout. A threshold fitted to one
document is a guess about every other document, so this sweeps them across the randomized
corpus and reports where the behaviour actually changes.

The outcome that matters is not the exact-match rate. Merging two columns loses facts;
*inventing* a column corrupts every line on the page, which is why it is counted separately
and why a setting that invents even one column is reported as unusable regardless of how many
exact matches it buys.

Detection is re-run on words already extracted once per document, so a sweep costs one PDF
parse per seed rather than one per combination.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from radiocorpus.evaluation.stress import StressPlan, plan, render
from radiocorpus.layout import segment as seg


@dataclass(frozen=True)
class Setting:
    min_gutter_pt: float
    occupancy_tolerance: float
    min_column_rows: int

    def key(self) -> str:
        return f"gutter={self.min_gutter_pt:g}pt,tolerance={self.occupancy_tolerance:g},rows={self.min_column_rows}"


DEFAULT = Setting(seg.MIN_GUTTER_PT, seg.GUTTER_OCCUPANCY_TOLERANCE, seg.MIN_COLUMN_ROWS)

SWEEP = [
    Setting(g, t, r)
    for g in (3.0, 6.0, 9.0, 12.0, 18.0)
    for t in (0.0, 0.15, 0.30)
    for r in (2, 3, 5)
]


def _pages(p: StressPlan) -> list[tuple[list[seg.Line], float]]:
    """Cluster each page's words once; the sweep then only re-runs detection."""
    import pdfplumber

    from radiocorpus.layout.backends import _words_from_pdfplumber_page

    out: list[tuple[list[seg.Line], float]] = []
    with pdfplumber.open(io.BytesIO(render(p))) as doc:
        for page in doc.pages:
            out.append((seg.cluster_lines(_words_from_pdfplumber_page(page)), float(page.width)))
    return out


def sweep(seeds: range | list[int], settings: list[Setting] | None = None) -> dict:
    plans = [plan(s) for s in seeds]
    prepared = [(p, _pages(p)) for p in plans]
    results: dict[str, dict] = {}

    original = (seg.GUTTER_OCCUPANCY_TOLERANCE, seg.MIN_COLUMN_ROWS)
    try:
        for setting in settings if settings is not None else SWEEP:
            # The two share-based thresholds are module constants consulted inside detection;
            # this measurement script sets them directly rather than threading a parameter
            # through the whole layout stack for a use nothing in production has.
            seg.GUTTER_OCCUPANCY_TOLERANCE = setting.occupancy_tolerance
            seg.MIN_COLUMN_ROWS = setting.min_column_rows
            tally = {"exact": 0, "conservative_merge": 0, "invented_columns": 0}
            for p, pages in prepared:
                detected = 1
                for lines, width in pages:
                    detected = max(detected, seg.detect_columns(lines, page_width=width, min_gutter=setting.min_gutter_pt).count)
                if detected == p.n_columns:
                    tally["exact"] += 1
                elif detected < p.n_columns:
                    tally["conservative_merge"] += 1
                else:
                    tally["invented_columns"] += 1
            tally["usable"] = tally["invented_columns"] == 0
            tally["exact_rate"] = round(tally["exact"] / len(prepared), 4) if prepared else None
            results[setting.key()] = tally
    finally:
        seg.GUTTER_OCCUPANCY_TOLERANCE, seg.MIN_COLUMN_ROWS = original

    best = max(
        (k for k, v in results.items() if v["usable"]),
        key=lambda k: results[k]["exact_rate"],
        default=None,
    )
    return {
        "documents": len(prepared),
        "in_use": DEFAULT.key(),
        "settings": results,
        "best_usable_setting": best,
        "settings_that_invent_columns": sorted(k for k, v in results.items() if not v["usable"]),
        "note": (
            "A setting is unusable if it invents a column on any document, however high its "
            "exact-match rate: a merged column loses facts, an invented one corrupts them."
        ),
    }


__all__ = ["DEFAULT", "SWEEP", "Setting", "sweep"]
