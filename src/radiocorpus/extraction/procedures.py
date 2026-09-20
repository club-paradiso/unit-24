"""Deterministic procedure-rule spotter. It finds sentences that prescribe a radio procedure
(readback, radio check, emergency traffic ...) and emits LOW-confidence candidates that carry
the sentence as the rule text. It never paraphrases."""

from __future__ import annotations

import re
from dataclasses import dataclass

from radiocorpus.extraction.text import TextBlock, squash

PROCEDURES: dict[str, re.Pattern[str]] = {
    "acknowledgement": re.compile(r"\backnowledg|\b10-4\b|\bcopy\b", re.I),
    "radio_check": re.compile(r"radio check|signal check", re.I),
    "repeat_request": re.compile(r"\brepeat\b|say again|\b10-9\b", re.I),
    "correction": re.compile(r"\bcorrection\b", re.I),
    "readback": re.compile(r"read ?back|repeat back|echo back", re.I),
    "emergency_traffic": re.compile(r"emergency traffic|\b10-33\b|officer needs (help|assistance)|\bmayday\b", re.I),
    "priority_traffic": re.compile(r"priority traffic|hold (the|all) (air|traffic)|clear the (air|channel)", re.I),
    "clearing_call": re.compile(r"\bclear(ed|ing)? (from|the) (call|scene)|\b10-8\b|\b10-98\b|back in service", re.I),
    "traffic_stop": re.compile(r"traffic stop|vehicle stop|\b10-38\b|\b11-95\b", re.I),
    "warrant_person_check": re.compile(r"warrant check|wants? and warrants|\b10-29\b|\b10-27\b|\b10-28\b|records? check", re.I),
    "vehicle_plate": re.compile(r"license plate|\bplate\b|registration", re.I),
    "location_address": re.compile(r"\blocation\b|\baddress\b|cross[- ]street", re.I),
    "numeric": re.compile(r"\bnumbers? (shall|should|must|are to) be|digit", re.I),
}
_PRESCRIPTIVE = re.compile(r"\b(shall|must|will|should|are to|is to|required|prohibited|only)\b", re.I)
_SENT = re.compile(r"(?<=[.;])\s+(?=[A-Z])")


@dataclass(frozen=True)
class ProcedureCandidate:
    procedure: str
    rule_text: str
    locator: str
    excerpt: str


def parse_procedure_blocks(blocks: list[TextBlock]) -> list[ProcedureCandidate]:
    out: list[ProcedureCandidate] = []
    seen: set[tuple[str, str]] = set()
    for b in blocks:
        text = squash(b.text)
        for sent in _SENT.split(text):
            s = sent.strip()
            if len(s) < 25 or len(s) > 400 or not _PRESCRIPTIVE.search(s):
                continue
            for proc, pat in PROCEDURES.items():
                if pat.search(s) and (proc, s.lower()) not in seen:
                    seen.add((proc, s.lower()))
                    out.append(ProcedureCandidate(procedure=proc, rule_text=s, locator=b.locator, excerpt=s[:200]))
    return out
