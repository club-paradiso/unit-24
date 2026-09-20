"""Deterministic agency-name normalization used for matching. Never used to rewrite the
canonical name; only to build comparison keys."""

from __future__ import annotations

import re

_ABBREV = {
    r"\bpd\b": "police department",
    r"\bso\b": "sheriff's office",
    r"\bsd\b": "sheriff's department",
    r"\bdept\.?\b": "department",
    r"\bdps\b": "department of public safety",
    r"\bhp\b": "highway patrol",
    r"\bsp\b": "state police",
    r"\buniv\.?\b": "university",
    r"\bco\.?\b": "county",
    r"\bst\.?\b": "saint",
    r"\bmt\.?\b": "mount",
    r"\bft\.?\b": "fort",
}
_STOP = {"the", "of", "and", "at"}
_SUFFIX_TOKENS = {"department", "office", "police", "sheriff", "sheriffs", "division", "bureau", "agency"}


def normalize_name(name: str) -> str:
    s = name.lower()
    s = s.replace("’", "'")
    s = re.sub(r"[.,()\-/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for pat, rep in _ABBREV.items():
        s = re.sub(pat, rep, s)
    s = s.replace("'s", "s").replace("'", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def name_tokens(name: str) -> list[str]:
    return [t for t in normalize_name(name).split(" ") if t and t not in _STOP]


def core_tokens(name: str) -> set[str]:
    """Tokens that identify the entity, ignoring generic suffix words."""
    return {t for t in name_tokens(name) if t not in _SUFFIX_TOKENS}


def split_reporting_unit(name: str) -> tuple[str, str | None]:
    """FBI UCR rosters encode sub-units as 'Agency: Qualifier'. Returns (agency, qualifier)."""
    if ":" in name:
        head, tail = name.split(":", 1)
        return head.strip(), tail.strip() or None
    return name.strip(), None
