"""Shared contextual tests used by every parser.

These decide *whether the surrounding text supports a reading*, never what the reading is.
Each returns the evidence it used so a candidate can carry its justification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------- numeric look-alikes

# A date written with dashes or slashes, in any common ordering, including 2- and 4-digit
# years. Matching the WHOLE token is what matters: "09-11-18" must never yield "11-18".
DATE_LIKE = re.compile(
    r"\b(?:\d{1,4}[-/.]\d{1,2}[-/.]\d{2,4})\b"
    r"|\b(?:\d{1,2}\s*[-/]\s*\d{1,2}\s*[-/]\s*\d{2,4})\b"
)
# Labels that introduce a revision or issue date.
DATE_LABEL = re.compile(
    r"\b(?:issued?|effective|revised?|revision|rev\.?|updated?|approved|amended|dated|supersedes?|expires?)\b[\s:]*",
    re.I,
)
# Statutory and ordinance citations: "23152 VC", "187 PC", "§ 10-4", "Title 5-3".
STATUTE = re.compile(r"\b\d{2,6}\s*(?:PC|VC|HS|BP|WI|CC|USC|CFR)\b|§\s*\d", re.I)
# Structural references: "Section 10-4", "Directive 7.1", "Appendix B-2".
STRUCTURAL_REF = re.compile(
    r"\b(?:section|sec\.?|chapter|chap\.?|article|appendix|annex|exhibit|attachment|directive|order|policy|"
    r"paragraph|para\.?|subsection|item|form|figure|table|page|pp?\.)\s*$",
    re.I,
)
PHONE_LIKE = re.compile(r"\(\d{3}\)\s*\d{3}[-–]\d{4}|\b\d{3}-\d{3}-\d{4}\b")


def numeric_token_is_date(text: str, start: int, end: int) -> bool:
    """True when the span at ``[start:end]`` lies inside a longer date-like number.

    Generalized rather than keyed to any literal: a code token is rejected when the character
    immediately before it is a digit-plus-separator, or the character after it is a
    separator-plus-digit, which is exactly what makes ``11-18`` a fragment of ``09-11-18``.
    """
    before = text[max(0, start - 4) : start]
    after = text[end : end + 4]
    if re.search(r"\d\s*[-/.]\s*$", before):
        return True
    if re.match(r"^\s*[-/.]\s*\d", after):
        return True
    for m in DATE_LIKE.finditer(text):
        if m.start() <= start and m.end() >= end:
            return True
    return False


def in_date_context(text: str, start: int) -> bool:
    """True when a revision/issue label precedes the span closely enough to govern it."""
    window = text[max(0, start - 40) : start]
    return bool(DATE_LABEL.search(window))


# ---------------------------------------------------------------- communication context

RADIO_TERMS = re.compile(
    r"\b(?:radio|radios|over the air|on the air|airwaves?|talkgroup|talk group|channel|frequency|frequencies|"
    r"dispatch(?:er|ers|ed|ing)?|dispatch centre|dispatch center|broadcast(?:s|ed|ing)?|transmit(?:s|ted|ting|ssion|ssions)?|"
    r"mobile data|mdt|mdc|scanner|repeater|base station|console|net control|"
    r"police radio|radio room|comm(?:unications?)? cent(?:er|re)|oemc|psap|9-?1-?1 cent(?:er|re)|rdc|"
    r"call sign|callsign|unit number|car number|badge over|ten[- ]code|10-\d{1,3}|11-\d{1,3}|signal \d{1,3})\b",
    re.I,
)
TELEPHONE_TERMS = re.compile(
    r"\b(?:telephone|phone call|landline|land line|cell ?phone|cellular|answering the (?:tele)?phone|"
    r"caller|callers|switchboard|voicemail|call(?:s|ed)? (?:in|back) by (?:tele)?phone|greeting)\b",
    re.I,
)
WRITTEN_TERMS = re.compile(
    r"\b(?:memorandum|memo|report form|paperwork|file copy|unit file|records[- ]retention|"
    r"e-?mail|letter|log ?book|written notice|forwarded to the unit secretary)\b",
    re.I,
)

ACTOR = re.compile(
    r"\b(?:officers?|members?|personnel|employees?|deputies|deputy|troopers?|units?|supervisors?|"
    r"dispatchers?|telecommunicators?|operators?|sergeants?|lieutenants?|commanders?|"
    r"police radio|radio room|oemc|rdc|department members?|assigned unit|responding units?)\b",
    re.I,
)
# Verbs that constitute an act of communication.
COMM_VERB = re.compile(
    r"\b(?:notif(?:y|ies|ied|ication)|advise[sd]?|advising|inform(?:s|ed)?|transmit(?:s|ted|ting)?|"
    r"broadcast(?:s|ed|ing)?|report(?:s|ed|ing)?(?! form)|request(?:s|ed|ing)?|acknowledge?(?:s|d|ment|ments)?|"
    r"respond(?:s|ed|ing)?|answer(?:s|ed|ing)?|state[sd]?|announce[sd]?|declare[sd]?|call(?:s|ed|ing)? out|"
    r"contact(?:s|ed|ing)?|relay(?:s|ed|ing)?|repeat(?:s|ed|ing)?|read ?back|give[sd]?|provide[sd]?|indicate[sd]?|"
    r"identif(?:y|ies|ied)|monitor(?:s|ed|ing)?|communicat(?:e|es|ed|ing|ion))\b",
    re.I,
)
# Verbs of physical movement: "sent to the location" is not "reported the location".
MOTION_VERB = re.compile(
    r"\b(?:sent|send|dispatched to|respond(?:s|ed|ing)? to|proceed(?:s|ed|ing)?|transport(?:s|ed|ing)?|"
    r"directed to|driven|drive[sn]?|travel(?:s|led|ling)?|return(?:s|ed|ing)? to the (?:station|district))\b",
    re.I,
)
PRESCRIPTIVE = re.compile(r"\b(?:shall|must|will|should|are to|is to|required|prohibited|may not|shall not|only)\b", re.I)
DEFINITIONAL = re.compile(
    r"\b(?:is defined as|are defined as|means?\b(?! of)|is not a\b|are not\b|refers? to|for (?:the )?purposes? of this|"
    r"definition|the term\b)",
    re.I,
)


class Medium:
    RADIO = "radio"
    TELEPHONE = "telephone"
    WRITTEN = "written"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CommContext:
    medium: str
    has_actor: bool
    has_comm_verb: bool
    is_prescriptive: bool
    is_definitional: bool
    evidence: tuple[str, ...]

    @property
    def is_radio(self) -> bool:
        return self.medium == Medium.RADIO


def analyse_communication(text: str, *, context: str = "") -> CommContext:
    """Classify the communication medium and the directive shape of a passage.

    ``context`` carries the enclosing heading and neighbouring text: a sentence inside a
    section titled "Radio Procedures" is radio even when the sentence itself omits the word.
    """
    evidence: list[str] = []
    radio_here = RADIO_TERMS.search(text)
    phone_here = TELEPHONE_TERMS.search(text)
    written_here = WRITTEN_TERMS.search(text)
    radio_ctx = RADIO_TERMS.search(context) if context else None
    phone_ctx = TELEPHONE_TERMS.search(context) if context else None

    medium = Medium.UNKNOWN
    if phone_here and not radio_here:
        medium, _ = Medium.TELEPHONE, evidence.append(f"telephone_term:{phone_here.group(0)!r}")
    elif written_here and not radio_here:
        medium, _ = Medium.WRITTEN, evidence.append(f"written_term:{written_here.group(0)!r}")
    elif radio_here:
        medium, _ = Medium.RADIO, evidence.append(f"radio_term:{radio_here.group(0)!r}")
    elif radio_ctx and not phone_ctx:
        medium, _ = Medium.RADIO, evidence.append(f"radio_term_in_context:{radio_ctx.group(0)!r}")
    elif phone_ctx:
        medium, _ = Medium.TELEPHONE, evidence.append(f"telephone_term_in_context:{phone_ctx.group(0)!r}")

    actor = ACTOR.search(text)
    verb = COMM_VERB.search(text)
    presc = PRESCRIPTIVE.search(text)
    defin = DEFINITIONAL.search(text)
    if actor:
        evidence.append(f"actor:{actor.group(0)!r}")
    if verb:
        evidence.append(f"comm_verb:{verb.group(0)!r}")
    if presc:
        evidence.append(f"prescriptive:{presc.group(0)!r}")
    if defin:
        evidence.append(f"definitional:{defin.group(0)!r}")
    return CommContext(
        medium=medium,
        has_actor=bool(actor),
        has_comm_verb=bool(verb),
        is_prescriptive=bool(presc),
        is_definitional=bool(defin),
        evidence=tuple(evidence),
    )


# Verbs that handle or dispose of a thing without communicating it.
HANDLING_VERB = re.compile(
    r"\b(?:take[sn]?|taking|obtain(?:s|ed|ing)?|determine[sd]?|determining|secure[sd]?|check(?:s|ed|ing)?|"
    r"search(?:es|ed|ing)?|establish(?:es|ed|ing)?|record(?:s|ed|ing)?|note[sd]?|verify|verifie[sd])\b",
    re.I,
)
_NON_COMM_VERB = re.compile("|".join([MOTION_VERB.pattern, HANDLING_VERB.pattern]), re.I)


def governed_by_comm_verb(text: str, topic: re.Pattern[str], *, window: int = 70) -> bool:
    """True when a topic term is the object of a communication verb.

    It is not enough for a communication verb to appear somewhere nearby: the *closest*
    preceding verb must be the communicating one. "advise the RDC of their location"
    qualifies; "notify a supervisor to take the officer's location" does not, because
    ``take`` intervenes and it is ``take`` that governs the location.
    """
    for m in topic.finditer(text):
        before = text[max(0, m.start() - window) : m.start()]
        comm = None
        for c in COMM_VERB.finditer(before):
            comm = c
        other = None
        for o in _NON_COMM_VERB.finditer(before):
            other = o
        if comm is None:
            continue
        if other is not None and other.start() > comm.start():
            continue  # a nearer, non-communicating verb governs the topic
        return True
    return False
