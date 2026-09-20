"""Date parsing helpers for document metadata. Unknown stays None."""

from __future__ import annotations

import re
from datetime import date

_MONTHS = {
    m: i
    for i, m in enumerate(
        ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1
    )
}
_MONTHS.update({k[:3]: v for k, v in list(_MONTHS.items())})

_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), lambda m: date(int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), lambda m: date(int(m[3]), int(m[1]), int(m[2]))),
    (re.compile(r"\b([A-Za-z]{3,9})\.? (\d{1,2}),? (\d{4})\b"), lambda m: date(int(m[3]), _MONTHS[m[1].lower()], int(m[2]))),
    (re.compile(r"\b(\d{1,2}) ([A-Za-z]{3,9})\.? (\d{4})\b"), lambda m: date(int(m[3]), _MONTHS[m[2].lower()], int(m[1]))),
]

_EFFECTIVE_HINT = re.compile(r"(effective|revised|rev\.?|issued|effective date|date issued|approved)[:\s]+", re.I)


def parse_date(text: str) -> date | None:
    for pat, fn in _PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return fn(m)
            except (KeyError, ValueError):
                continue
    return None


def find_effective_date(text: str, window: int = 40) -> date | None:
    """Look for a date that follows an 'Effective/Revised/Issued' hint. Returns None when absent —
    an undated manual must stay undated."""
    for m in _EFFECTIVE_HINT.finditer(text):
        d = parse_date(text[m.end() : m.end() + window])
        if d:
            return d
    return None
