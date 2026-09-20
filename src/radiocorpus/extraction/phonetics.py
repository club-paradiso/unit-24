"""Deterministic phonetic-alphabet parser. Recognises 'A - Adam', 'A Adam', 'A: Alpha',
'Alpha (A)' patterns and table rows 'A | Adam'. Assigns a system label only by comparing the
recovered word set with reference alphabets; otherwise 'LOCAL'/'UNKNOWN'."""

from __future__ import annotations

import re
from dataclasses import dataclass

from radiocorpus.extraction.text import TextBlock

NATO = {
    "A": "ALFA",
    "B": "BRAVO",
    "C": "CHARLIE",
    "D": "DELTA",
    "E": "ECHO",
    "F": "FOXTROT",
    "G": "GOLF",
    "H": "HOTEL",
    "I": "INDIA",
    "J": "JULIETT",
    "K": "KILO",
    "L": "LIMA",
    "M": "MIKE",
    "N": "NOVEMBER",
    "O": "OSCAR",
    "P": "PAPA",
    "Q": "QUEBEC",
    "R": "ROMEO",
    "S": "SIERRA",
    "T": "TANGO",
    "U": "UNIFORM",
    "V": "VICTOR",
    "W": "WHISKEY",
    "X": "XRAY",
    "Y": "YANKEE",
    "Z": "ZULU",
}
NATO_VARIANTS = {"ALPHA": "ALFA", "JULIET": "JULIETT", "X-RAY": "XRAY"}
# Reference alphabets used only to LABEL a recovered alphabet; they never populate agency facts.
APCO_1941 = {
    "A": "ADAM",
    "B": "BOY",
    "C": "CHARLES",
    "D": "DAVID",
    "E": "EDWARD",
    "F": "FRANK",
    "G": "GEORGE",
    "H": "HENRY",
    "I": "IDA",
    "J": "JOHN",
    "K": "KING",
    "L": "LINCOLN",
    "M": "MARY",
    "N": "NORA",
    "O": "OCEAN",
    "P": "PAUL",
    "Q": "QUEEN",
    "R": "ROBERT",
    "S": "SAM",
    "T": "TOM",
    "U": "UNION",
    "V": "VICTOR",
    "W": "WILLIAM",
    "X": "XRAY",
    "Y": "YOUNG",
    "Z": "ZEBRA",
}

_PAIR = re.compile(r"(?<![A-Za-z])(?P<letter>[A-Z])\s*(?:[-–:=|.]|\s)\s*(?P<word>[A-Z][a-z]{2,10}|[A-Z]{3,10}|X-?[Rr]ay)(?![a-z])")
_PAIR_REV = re.compile(r"(?P<word>[A-Z][a-z]{2,10}|[A-Z]{3,10})\s*\(\s*(?P<letter>[A-Z])\s*\)")


@dataclass(frozen=True)
class PhoneticCandidate:
    letter: str
    word: str
    locator: str
    excerpt: str


def _clean(w: str) -> str:
    w = w.upper().replace("-", "")
    return NATO_VARIANTS.get(w, w)


def parse_phonetic_blocks(blocks: list[TextBlock]) -> list[PhoneticCandidate]:
    out: list[PhoneticCandidate] = []
    seen: set[tuple[str, str]] = set()
    for b in blocks:
        for line in b.text.splitlines():
            for m in list(_PAIR.finditer(line)) + list(_PAIR_REV.finditer(line)):
                letter, word = m["letter"].upper(), m["word"]
                w = _clean(word)
                if not w.startswith(letter):
                    continue  # a phonetic word begins with its letter; anything else is noise
                if (letter, w) in seen:
                    continue
                seen.add((letter, w))
                out.append(PhoneticCandidate(letter=letter, word=w, locator=b.locator, excerpt=line.strip()[:200]))
    return out


def label_system(cands: list[PhoneticCandidate]) -> tuple[str, float]:
    """Return (label, coverage). Label is NATO / APCO_1941 / LOCAL / UNKNOWN based on overlap;
    coverage is the fraction of 26 letters recovered."""
    letters = {c.letter: c.word for c in cands}
    coverage = len(letters) / 26
    if len(letters) < 13:
        return "UNKNOWN", coverage
    nato = sum(1 for k, v in letters.items() if NATO.get(k) == v)
    apco = sum(1 for k, v in letters.items() if APCO_1941.get(k) == v)
    if nato / len(letters) >= 0.9:
        return "NATO", coverage
    if apco / len(letters) >= 0.9:
        return "APCO_1941", coverage
    return "LOCAL", coverage
