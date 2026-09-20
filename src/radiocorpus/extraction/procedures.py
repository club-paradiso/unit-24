"""Context-aware procedure-rule extraction.

The previous version emitted a candidate whenever a prescriptive word and a keyword shared a
sentence. On real documents that classified records-retention notes as radio
acknowledgement, impound paperwork as plate transmission, and a telephone greeting as a
location protocol.

A candidate now has to survive four questions:

* **Medium** — is this about radio, or about a telephone call, a form, or a memo?
* **Actor** — who is directed to act?
* **Act** — is there an act of communication, rather than movement or filing?
* **Object** — is the topic of the rule what the communication verb governs?

The surrounding section heading and the neighbouring sentences are carried with the
candidate, because several audited rules were unusable purely because their condition or
exception sat in the next clause.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from radiocorpus.extraction.context import (
    Medium,
    analyse_communication,
    governed_by_comm_verb,
)
from radiocorpus.extraction.text import TextBlock, squash
from radiocorpus.layout.model import BlockType, DocumentLayout, LayoutBlock

PARSER_RULE = "procedure_rule:contextual"
PARSER_VERSION = "3"

MIN_RULE_CHARS = 25
MAX_RULE_CHARS = 400
CONTEXT_CHARS = 320


@dataclass(frozen=True, slots=True)
class Trigger:
    pattern: re.Pattern[str]
    # When set, the topic must be the object of a communication verb, not of motion.
    object_of_comm: re.Pattern[str] | None = None
    # Require an explicit radio medium rather than allowing inherited section context.
    require_explicit_radio: bool = False


TRIGGERS: dict[str, Trigger] = {
    # "copy" as a bare noun is deliberately absent: in the audited corpus every candidate it
    # produced was a document copy, never a radio acknowledgement.
    "acknowledgement": Trigger(
        re.compile(r"\backnowledg(?:e|es|ed|ing|ement|ments?)\b|\b10-4\b|\"copy\"|“copy”|\bcopies the transmission\b", re.I)
    ),
    "radio_check": Trigger(re.compile(r"\bradio check\b|\bsignal check\b|\bcomm(?:unications?)? check\b", re.I)),
    "repeat_request": Trigger(re.compile(r"\bsay again\b|\b10-9\b|\brepeat (?:the )?(?:last )?transmission\b", re.I)),
    "correction": Trigger(re.compile(r"\bcorrection\b|\bdisregard (?:the )?(?:last|previous)\b", re.I)),
    "readback": Trigger(re.compile(r"\bread ?back\b|\brepeat(?:s|ed)? back\b|\becho back\b", re.I)),
    "emergency_traffic": Trigger(
        re.compile(r"\bemergency traffic\b|\b10-33\b|\bofficer needs? (?:help|assistance)\b|\bmayday\b|\bassist officer\b", re.I)
    ),
    "priority_traffic": Trigger(
        re.compile(r"\bpriority traffic\b|\bhold (?:the|all) (?:air|traffic)\b|\bclear the (?:air|channel|frequency)\b|\brestricted traffic\b", re.I)
    ),
    "clearing_call": Trigger(
        re.compile(r"\bback in service\b|\breturn to service\b|\b10-8\b|\b10-98\b|\bclear(?:ed|ing)? (?:from )?the (?:call|scene)\b", re.I)
    ),
    "traffic_stop": Trigger(re.compile(r"\btraffic stop\b|\bvehicle stop\b|\b10-38\b|\b11-95\b|\bstopping a vehicle\b", re.I)),
    "warrant_person_check": Trigger(
        re.compile(r"\bwarrant check\b|\bwants? and warrants?\b|\b10-29\b|\b10-27\b|\b10-28\b|\brecords? check\b|\bcheck for wants\b", re.I)
    ),
    "vehicle_plate": Trigger(
        re.compile(r"\blicense plate\b|\bregistration (?:number|check)\b|\bplate number\b", re.I),
        object_of_comm=re.compile(r"\b(?:license )?plate\b|\bregistration\b", re.I),
    ),
    "location_address": Trigger(
        re.compile(r"\blocation\b|\baddress\b|\bcross[- ]street\b", re.I),
        object_of_comm=re.compile(r"\blocation\b|\baddress\b|\bcross[- ]street\b", re.I),
    ),
    # "\\bdigit" used to match "Digital", turning a repeater request into a numeric rule.
    "numeric": Trigger(re.compile(r"\bdigits?\b|\bnumbers? (?:shall|should|must|are to|will) be\b|\bphonetically\b", re.I)),
}

# Sentence break: also break before a list enumerator even when it is lower-case, which the
# previous splitter could not do and which merged unrelated instructions together.
_SENT_SPLIT = re.compile(r"(?<=[.;])\s+(?=(?:[A-Z0-9“\"]|[a-z]\s*[.)]\s))")
_TRAILING_ENUM = re.compile(r"\s+(?:[a-zA-Z]|\d{1,2})\s*[.)]\s*$")
_LEADING_ENUM = re.compile(r"^\s*(?:[a-zA-Z]|\d{1,3})\s*[.)]\s+")
_DANGLING_SUBJECT = re.compile(r"^\s*(?:this|that|these|those|it|they|he|she|such|the (?:same|above|foregoing))\b", re.I)
_EXCEPTION = re.compile(
    r"\b(?:unless|except|however|provided that|but (?:not|only)|if (?:feasible|possible|practical)|when (?:practical|feasible))\b",
    re.I,
)
_OPEN_ENDED = re.compile(r"(?:;|\band)\s*$", re.I)
_CONDITION = re.compile(r"\b(?:if|when|while|upon|whenever|during|before|after|once|in the event)\b", re.I)


@dataclass(frozen=True)
class ProcedureCandidate:
    procedure: str
    rule_text: str
    locator: str
    excerpt: str
    structural_reason: str = "text_only"
    evidence: tuple[str, ...] = ()
    section_heading: str | None = None
    section_path: tuple[str, ...] = ()
    context_before: str | None = None
    context_after: str | None = None
    medium: str = Medium.UNKNOWN
    has_condition: bool = False
    has_exception: bool = False
    context_complete: bool = True
    crosses_page: bool = False
    parser_rule: str = PARSER_RULE
    parser_version: str = PARSER_VERSION
    page_number: int | None = None


@dataclass(slots=True)
class _Unit:
    """One sentence with everything needed to interpret it."""

    text: str
    block: LayoutBlock
    before: str
    after: str
    heading: LayoutBlock | None
    path: tuple[str, ...]
    crosses_page: bool = False


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(squash(text)) if p.strip()]
    out: list[str] = []
    for p in parts:
        p = _TRAILING_ENUM.sub("", p)  # drop a dangling "2." / "c." captured from the next item
        p = _LEADING_ENUM.sub("", p)
        if p:
            out.append(p)
    return out


def _units(layout: DocumentLayout) -> list[_Unit]:
    blocks = [b for b in layout.included_blocks() if b.text.strip()]
    headings: list[LayoutBlock] = []
    units: list[_Unit] = []
    # Flatten to sentences while remembering neighbours, including across a page break.
    flat: list[tuple[LayoutBlock, str, LayoutBlock | None, tuple[str, ...]]] = []
    for b in blocks:
        if b.block_type is BlockType.HEADING:
            headings.append(b)
            continue
        heading = headings[-1] if headings else None
        path = tuple(h.text.strip()[:80] for h in headings[-2:])
        for s in split_sentences(b.text):
            flat.append((b, s, heading, path))
    for i, (b, s, heading, path) in enumerate(flat):
        prev_b, prev_s = (flat[i - 1][0], flat[i - 1][1]) if i > 0 else (None, "")
        next_b, next_s = (flat[i + 1][0], flat[i + 1][1]) if i + 1 < len(flat) else (None, "")
        crosses = bool((prev_b and prev_b.page_number != b.page_number) or (next_b and next_b.page_number != b.page_number))
        units.append(
            _Unit(
                text=s,
                block=b,
                before=prev_s[-CONTEXT_CHARS:],
                after=next_s[:CONTEXT_CHARS],
                heading=heading,
                path=path,
                crosses_page=crosses,
            )
        )
    return units


def parse_procedures(layout: DocumentLayout) -> list[ProcedureCandidate]:
    out: list[ProcedureCandidate] = []
    seen: set[tuple[str, str]] = set()
    for unit in _units(layout):
        s = unit.text
        if not (MIN_RULE_CHARS <= len(s) <= MAX_RULE_CHARS):
            continue
        heading_text = unit.heading.text if unit.heading else ""
        context = " ".join([heading_text, " ".join(unit.path), unit.before, unit.after])
        comm = analyse_communication(s, context=context)
        if not comm.is_prescriptive:
            continue
        if comm.is_definitional and not comm.has_comm_verb:
            continue
        if comm.medium in (Medium.TELEPHONE, Medium.WRITTEN):
            continue  # a phone greeting or a file copy is not a radio procedure
        if not comm.is_radio:
            continue
        if not comm.has_comm_verb:
            continue
        if not (comm.has_actor or _is_imperative(s)):
            continue
        for proc, trig in TRIGGERS.items():
            if not trig.pattern.search(s):
                continue
            if trig.object_of_comm is not None and not governed_by_comm_verb(s, trig.object_of_comm):
                continue
            if trig.require_explicit_radio and Medium.RADIO not in comm.medium:
                continue
            key = (proc, s.lower())
            if key in seen:
                continue
            seen.add(key)
            has_exc = bool(_EXCEPTION.search(s))
            exc_next = bool(_EXCEPTION.search(unit.after[:160]))
            dangling = bool(_DANGLING_SUBJECT.match(s)) or not (comm.has_actor or _is_imperative(s))
            # A clause closing with ";" or "and" is one item of a list that continues; its
            # qualifying exception may sit in the next item, so it cannot stand alone.
            open_ended = bool(_OPEN_ENDED.search(s))
            complete = not dangling and not open_ended and not (exc_next and not has_exc)
            evidence = list(comm.evidence) + [f"trigger:{proc}", f"block:{unit.block.block_type}"]
            if unit.heading:
                evidence.append(f"section:{unit.heading.text[:60]!r}")
            if exc_next and not has_exc:
                evidence.append("exception_in_following_sentence")
            if dangling:
                evidence.append("antecedent_outside_sentence")
            if open_ended:
                evidence.append("clause_continues_in_next_list_item")
            out.append(
                ProcedureCandidate(
                    procedure=proc,
                    rule_text=s,
                    locator=unit.block.locator,
                    excerpt=s[:300],
                    structural_reason="SECTION_CONTEXT" if unit.heading else "SENTENCE_CONTEXT",
                    evidence=tuple(evidence),
                    section_heading=heading_text[:160] or None,
                    section_path=unit.path,
                    context_before=unit.before or None,
                    context_after=unit.after or None,
                    medium=comm.medium,
                    has_condition=bool(_CONDITION.search(s)),
                    has_exception=has_exc,
                    context_complete=complete,
                    crosses_page=unit.crosses_page,
                    page_number=unit.block.page_number,
                )
            )
    out.sort(key=lambda c: (c.page_number or 0, c.locator, c.procedure))
    return out


_IMPERATIVE = re.compile(
    r"^(?:upon|when|while|if|once|before|after|during)\b[^.]{0,80}?,\s*(?:[a-z]+\s+){0,3}"
    r"(?:notify|advise|inform|transmit|broadcast|report|request|acknowledge|respond|answer|state|give|provide|contact|return|conduct|repeat)\b"
    r"|^(?:notify|advise|inform|transmit|broadcast|report|request|acknowledge|respond|answer|state|give|provide|contact|return|conduct|repeat)\b",
    re.I,
)


def _is_imperative(sentence: str) -> bool:
    """A directive with an implied addressee, e.g. 'Upon completing the assignment, return to service…'."""
    return bool(_IMPERATIVE.search(sentence))


def parse_procedure_blocks(blocks: list[TextBlock]) -> list[ProcedureCandidate]:
    """Legacy entry point operating on flattened text."""
    from radiocorpus.extraction.codes import _layout_from_text_blocks

    return parse_procedures(_layout_from_text_blocks(blocks))


__all__ = ["TRIGGERS", "ProcedureCandidate", "parse_procedure_blocks", "parse_procedures", "split_sentences"]
