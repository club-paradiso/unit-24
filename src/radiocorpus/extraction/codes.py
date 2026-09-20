"""Deterministic parser for code tables (10-codes, 11-codes, signal codes, status/disposition
codes). Emits candidates with exact locators and short excerpts. It does NOT decide what a
code means beyond what the text says on that line."""

from __future__ import annotations

import re
from dataclasses import dataclass

from radiocorpus.extraction.text import TextBlock, squash

# "10-4  Acknowledgement", "10-4: Acknowledged", "10-4 | Acknowledged" (html table), "Code 3 Emergency response",
# "Signal 7 Dead person", "11-99 Officer needs help"
_CODE = re.compile(
    r"(?P<code>(?:10|11|12|13)\s?-\s?\d{1,3}[A-Za-z]?|(?:Code|Signal|Status)\s?-?\s?\d{1,3}[A-Za-z]?)"
    r"\s*[:\-–|.]?\s*(?P<meaning>[A-Za-z(][^|\n]{2,120}?)(?=\s{2,}|\s*\||\s*$|\s+(?:10|11|12|13)\s?-\s?\d)",
    re.I,
)
_FALSE_CONTEXT = re.compile(r"(section|chapter|page|paragraph|policy|order|rev|revised|figure|table)\s*$", re.I)


@dataclass(frozen=True)
class CodeCandidate:
    code_system: str
    code: str
    meaning: str
    raw: str
    locator: str
    excerpt: str


def normalize_code(code: str) -> tuple[str, str]:
    c = squash(code).upper().replace(" -", "-").replace("- ", "-").replace(" ", "")
    if c.startswith("10-"):
        return "TEN_CODE", c
    if c.startswith("11-"):
        return "ELEVEN_CODE", c
    if c.startswith("12-") or c.startswith("13-"):
        return "OTHER", c
    m = re.match(r"(CODE|SIGNAL|STATUS)-?(\d{1,3}[A-Z]?)", c)
    if m:
        sysname = {"CODE": "CODE", "SIGNAL": "SIGNAL", "STATUS": "STATUS"}[m[1]]
        return sysname, f"{m[1]} {m[2]}"
    return "OTHER", c


def parse_code_blocks(blocks: list[TextBlock]) -> list[CodeCandidate]:
    out: list[CodeCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for b in blocks:
        for line in b.text.splitlines():
            line_s = line.strip()
            if not line_s:
                continue
            for m in _CODE.finditer(line_s):
                pre = line_s[: m.start()].strip()
                if _FALSE_CONTEXT.search(pre):
                    continue
                sysname, code = normalize_code(m["code"])
                meaning = squash(m["meaning"]).rstrip(" .;,")
                if len(meaning) < 3 or meaning.lower() in {"and", "or", "the"}:
                    continue
                key = (b.locator, code, meaning.lower())
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    CodeCandidate(code_system=sysname, code=code, meaning=meaning, raw=m.group(0).strip(), locator=b.locator, excerpt=line_s[:200])
                )
    return out
