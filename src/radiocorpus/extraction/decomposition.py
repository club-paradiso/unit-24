"""Decompose a procedure sentence into the parts that make it a fact.

A rule is not a fact until you can say **who** must do **what** communicative act **to what**.
Until now a procedure candidate carried a sentence and a topic label, so the adjudication of
the four real documents could record that its applicability scope was wrong without ever
recording which part was wrong — 27 candidates, 0 complete facts, and nothing to act on.

Everything here is located, never inferred. Each element is a span of the sentence itself,
carrying its offsets and the rule that found it, so a reviewer can check the claim against the
source by looking at the characters it came from. Nothing is supplied from knowledge of what
police procedures usually say: if the sentence does not state an actor, the actor is absent,
and the candidate says so rather than filling the gap with a plausible one. That asymmetry is
deliberate. A missing actor costs a fact; an invented one is a false fact about an agency.

Two sentence shapes are handled, and everything else fails closed:

``<actor> <modal> <communication verb> <object>``
    "Units will acknowledge the radio transmission."

``<actor> <modal> <communication verb> <recipient> of|about|that <object>``
    "Members shall advise the dispatcher of their location."

The second shape matters more than its frequency suggests. In "advise the dispatcher of their
location" the grammatical object is the dispatcher, but the thing *communicated* is the
location, and a decomposition that reports the dispatcher has recorded the wrong fact.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from radiocorpus.extraction.context import COMM_VERB, DATE_LABEL, DATE_LIKE, HANDLING_VERB, MOTION_VERB

DECOMPOSITION_VERSION = "decomposition-1"

#: Modals that introduce a directed act. ``may`` is included because a permission still names
#: an actor and an act; whether a permission is a rule is a question for eligibility, not here.
MODAL = re.compile(r"\b(?:shall(?:\s+not)?|must(?:\s+not)?|will(?:\s+not)?|should(?:\s+not)?|are to|is to|may(?:\s+not)?)\b", re.I)
#: A leading subordinate clause: "When a unit is dispatched, members shall …". The actor is on
#: the far side of the comma, so the clause is stepped over rather than read as the subject.
#: No ``^``: this is matched from a position, and ``^`` would anchor to the start of the string
#: regardless of that position, which silently disables the rule once anything precedes it.
_LEADING_CLAUSE = re.compile(
    r"\s*(?:when|whenever|if|upon|before|after|while|during|once|in the event|as soon as|should)\b[^,]{0,120},\s*",
    re.I,
)
#: Furniture that labels a passage rather than taking part in it. A rule printed under a NOTE
#: heading directs the same people as one printed without it, but the label sits inside the
#: sentence the text extractor produces, and it both contaminates the subject — a real
#: directive yielded the actor "NOTE: If feasible, officers" — and hides the leading clause
#: behind it from the rule above. These labels are general technical-document furniture, not
#: any agency's vocabulary, which is why matching them by name is a format rule and not a
#: branch on whose document this is.
_FURNITURE_LABEL = re.compile(
    r"\s*(?:note|notes|caution|warning|important|exception|reminder|example)\b\s*[:.\-–]?\s+",
    re.I,
)
#: Adverbs that can sit between the modal and its verb: "shall immediately notify".
_INTERVENING = r"(?:\b(?:not|then|also|immediately|promptly|first|next|thereafter|as soon as practical(?:le)?|"
_INTERVENING += r"without delay|at once|normally|ordinarily|generally|always|never)\b\s+){0,3}"
#: Markers that separate a recipient from the thing actually communicated.
_CONTENT_MARKER = re.compile(r"\b(?:of|about|regarding|concerning|as to|that|whether)\b", re.I)
#: ``that`` and ``whether`` introduce a clause, and a clause is not a noun phrase. Reading one
#: as a noun phrase truncated "that he or she is monitoring the pursuit" to "he", which reports
#: a pronoun as the thing communicated.
_CLAUSE_MARKER = re.compile(r"^(?:that|whether)$", re.I)
MAX_CLAUSE_CHARS = 160
#: Tokens that close a noun phrase. An adjunct starts here, and so does a condition — and so
#: does a content marker, because "advise the dispatcher of their location" is a recipient and
#: a message, not one long thing. Letting the phrase run through "of" is what made the first
#: version report the dispatcher as part of what was communicated.
_NP_STOP = re.compile(
    r"\b(?:on|in|at|by|with|from|for|to|before|after|when|whenever|while|during|upon|until|unless|"
    r"except|if|and|or|via|over|through|per|using|prior to|pursuant to|in accordance with|"
    r"of|about|regarding|concerning|as to|that|whether)\b|[;:,.]",
    re.I,
)
_ARTICLE = r"(?:the|a|an|their|his|her|its|our|all|any|each|every|both|this|these|those|such)"
#: A noun phrase: an optional determiner and up to six further words.
_NP = re.compile(rf"\s*(?P<np>(?:{_ARTICLE}\s+)?[\w'’-]+(?:\s+[\w'’-]+){{0,5}})", re.I)
_NON_COMM_VERB = re.compile("|".join([MOTION_VERB.pattern, HANDLING_VERB.pattern]), re.I)
#: ``will be broadcast``, ``shall be transmitted``. In a passive the phrase before the modal is
#: what the act is done *to*, not who does it, and reading it as the actor states something the
#: document does not: "The location will be relayed" does not direct the location to do
#: anything. Found on a real sentence, where it produced a complete decomposition with the
#: wrong actor — the worst possible outcome.
_PASSIVE = re.compile(r"\s*(?:not\s+)?(?:be|been|being)\b", re.I)
#: An agent may be named in a by-phrase, but a by-phrase is as often a means ("by unit number",
#: "by radio"). It is taken only when the phrase names a role, the same confirmation the
#: ambiguous ``of`` reading requires.
_BY_AGENT = re.compile(r"\bby\s+(?P<agent>(?:the|a|an)?\s*[\w'’-]+(?:\s+[\w'’-]+){0,3})", re.I)
#: A section number glued to the front of a subject: "2.1 - Canadian Provinces These codes".
_LEADING_ENUMERATOR = re.compile(r"^\s*(?:\d{1,3}(?:\.\d{1,3})*|[A-Za-z])\s*[-–.):]\s*")
#: The longest an actor phrase may be before it stops looking like a subject.
MAX_ACTOR_CHARS = 110
MAX_OBJECT_WORDS = 6


@dataclass(frozen=True)
class Span:
    """A claim, and the characters of the sentence it was read from."""

    text: str
    start: int
    end: int
    rule: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Decomposition:
    """Who must do what communicative act to what, as far as the sentence states it."""

    actor: Span | None = None
    communication_action: Span | None = None
    governed_object: Span | None = None
    #: Extracted to disambiguate the object in the ditransitive shape, and reported as
    #: evidence rather than as a claim: nothing scores it, so it is not offered as a fact.
    recipient: Span | None = None
    actor_is_implied: bool = False
    evidence: tuple[str, ...] = ()
    version: str = DECOMPOSITION_VERSION

    @property
    def complete(self) -> bool:
        """All three claims located. An implied actor is not a stated one."""
        return bool(self.actor and self.communication_action and self.governed_object)

    def to_dict(self) -> dict:
        return {
            "actor": self.actor.to_dict() if self.actor else None,
            "communication_action": self.communication_action.to_dict() if self.communication_action else None,
            "governed_object": self.governed_object.to_dict() if self.governed_object else None,
            "recipient": self.recipient.to_dict() if self.recipient else None,
            "actor_is_implied": self.actor_is_implied,
            "complete": self.complete,
            "evidence": list(self.evidence),
            "version": self.version,
        }


def _trim(text: str, start: int, end: int) -> tuple[str, int, int]:
    """Tighten a span onto its own characters, so offsets always address the quoted text."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ",;:."):
        end -= 1
    return text[start:end], start, end


def _message(sentence: str, marker: re.Match[str], *, rule: str) -> Span | None:
    """What follows a content marker: a clause for ``that``/``whether``, otherwise a phrase."""
    if _CLAUSE_MARKER.match(marker.group(0)):
        end = min(len(sentence), marker.end() + MAX_CLAUSE_CHARS)
        cut = ""
        if end < len(sentence):
            # A span addresses characters of the source, so a reader checks the claim by reading
            # them. Stopping at the cap mid-word produced "… number of occupants … on th", which
            # is not a quotation of anything. Back off to a word boundary and say it was cut.
            boundary = sentence.rfind(" ", marker.end(), end)
            if boundary > marker.end():
                end = boundary
            cut = "_truncated"
        text, start, end = _trim(sentence, marker.end(), end)
        return Span(text=text, start=start, end=end, rule=f"{rule}_clause{cut}") if text else None
    return _noun_phrase(sentence, marker.end(), rule=rule)


def _noun_phrase(sentence: str, at: int, *, rule: str) -> Span | None:
    """The noun phrase beginning at ``at``, ending where an adjunct or clause begins."""
    m = _NP.match(sentence, at)
    if not m:
        return None
    start, end = m.start("np"), m.end("np")
    stop = _NP_STOP.search(sentence, start, end)
    if stop is not None:
        end = stop.start()
    text, start, end = _trim(sentence, start, end)
    if not text or len(text.split()) > MAX_OBJECT_WORDS:
        return None
    # A bare determiner is not a noun phrase.
    if re.fullmatch(_ARTICLE, text, re.I):
        return None
    return Span(text=text, start=start, end=end, rule=rule)


def _passive_agent(sentence: str, after: int) -> tuple[Span | None, list[str]]:
    """The agent of a passive, when the sentence names one and it reads as a role."""
    from radiocorpus.extraction.context import ACTOR

    m = _BY_AGENT.search(sentence, after)
    if m is None:
        return None, ["passive_voice:agent_unstated"]
    text, start, end = _trim(sentence, m.start("agent"), m.end("agent"))
    stop = _NP_STOP.search(text)
    if stop is not None:
        text, start, end = _trim(sentence, start, start + stop.start())
    if not text or not ACTOR.search(text):
        return None, [f"passive_voice:by_phrase_is_not_a_role:{text!r}"]
    return Span(text=text, start=start, end=end, rule="passive_by_agent"), ["passive_voice:agent_named"]


def _find_actor(sentence: str, modal: re.Match[str]) -> tuple[Span | None, list[str]]:
    """The subject: everything from the start of the main clause up to the modal.

    Read structurally rather than from a list of job titles. A department that calls its people
    something this project has never heard of still gets an actor, and no list has to be kept
    current for a new agency to work.
    """
    evidence: list[str] = []
    begin = 0
    label = _FURNITURE_LABEL.match(sentence)
    if label:
        begin = label.end()
        evidence.append(f"dropped_document_furniture_label:{label.group(0).strip()!r}")
    lead = _LEADING_CLAUSE.match(sentence, begin)
    if lead:
        begin = lead.end()
        evidence.append(f"stepped_over_leading_clause:{lead.group(0).strip()[:40]!r}")
    if _PASSIVE.match(sentence, modal.end()):
        agent, why = _passive_agent(sentence, modal.end())
        return agent, evidence + why
    text, start, end = _trim(sentence, begin, modal.start())
    enumerator = _LEADING_ENUMERATOR.match(text)
    if enumerator:
        start += enumerator.end()
        text, start, end = _trim(sentence, start, end)
        evidence.append("dropped_leading_enumerator")
    # A date is never part of who must act. When a revision stamp has been glued onto the
    # front of a sentence the subject begins after it, and reporting the stamp as the actor
    # would be a false statement about which people the rule directs.
    last_date = None
    for m in DATE_LIKE.finditer(text):
        last_date = m
    if last_date is not None:
        start += last_date.end()
        text, start, end = _trim(sentence, start, end)
        evidence.append("dropped_leading_date_stamp")
    elif DATE_LABEL.match(text):
        return None, evidence + ["subject_is_a_date_label"]
    if not text:
        return None, evidence + ["no_subject_before_modal"]
    if len(text) > MAX_ACTOR_CHARS:
        return None, evidence + [f"subject_too_long:{len(text)}"]
    if MODAL.search(text):
        return None, evidence + ["second_modal_inside_subject"]
    return Span(text=text, start=start, end=end, rule="subject_before_modal"), evidence


def _find_action(sentence: str, after: int) -> tuple[Span | None, list[str]]:
    """The communication verb the modal governs.

    The *nearest* verb after the modal has to be the communicating one, for the same reason
    ``governed_by_comm_verb`` insists on it: in "shall take the location and report it" the
    verb that governs the location is ``take``, and reading ``report`` as the act would attach
    the rule to the wrong action.
    """
    window = sentence[after:]
    intervening = re.match(_INTERVENING, window, re.I)
    offset = after + (intervening.end() if intervening else 0)
    comm = COMM_VERB.search(sentence, offset)
    other = _NON_COMM_VERB.search(sentence, offset)
    if comm is None:
        return None, ["no_communication_verb_after_modal"]
    if other is not None and other.start() < comm.start():
        return None, [f"nearer_non_communication_verb:{other.group(0)!r}"]
    if comm.start() > offset + 40:
        return None, [f"communication_verb_too_far_from_modal:{comm.start() - offset}"]
    text, start, end = _trim(sentence, comm.start(), comm.end())
    return Span(text=text, start=start, end=end, rule="comm_verb_after_modal"), []


_DETERMINED = re.compile(rf"^\s*{_ARTICLE}\b", re.I)
#: ``to`` followed by a verb is an infinitive; ``to`` followed by anything else is a recipient
#: phrase ("transmit the location to Police Radio"), where the noun phrase before it really is
#: the thing communicated. Only a verb the project already knows counts, so an unrecognised word
#: leaves the existing reading alone rather than discarding a correct object.
_TO_INFINITIVE = re.compile(rf"\s*to\s+(?P<verb>{COMM_VERB.pattern}|{_NON_COMM_VERB.pattern})", re.I)


def _find_object(sentence: str, after: int) -> tuple[Span | None, Span | None, list[str]]:
    """What the act communicates, and to whom when the sentence separates the two.

    ``of`` is the hard case, because it both separates a recipient from a message ("the
    dispatcher **of** their location") and binds a compound title ("the chief **of** police").
    The reading is confirmed rather than assumed: a determined or possessed second phrase is a
    message, and so is one whose first phrase names a role. Anything else is genuinely
    ambiguous and yields no object at all, because a wrong object is a false fact about an
    agency while a missing one is only a gap.
    """
    from radiocorpus.extraction.context import ACTOR

    first = _noun_phrase(sentence, after, rule="np_after_comm_verb")
    if first is None:
        # "acknowledge to the dispatcher that …": the recipient is marked by a preposition
        # rather than sitting bare after the verb, and the message follows the marker.
        to = re.match(r"\s*to\b", sentence[after:], re.I)
        if to is None:
            return None, None, ["no_noun_phrase_after_verb"]
        recipient = _noun_phrase(sentence, after + to.end(), rule="np_after_to")
        if recipient is None:
            return None, None, ["no_recipient_after_to"]
        marker = _CONTENT_MARKER.match(sentence, _skip_space(sentence, recipient.end))
        if marker is None:
            return None, recipient, ["recipient_after_to_without_message"]
        message = _message(sentence, marker, rule=f"after_to_{marker.group(0).lower()}")
        if message is None:
            return None, recipient, [f"content_marker_without_object:{marker.group(0)!r}"]
        return message, recipient, [f"to_recipient_then_content:{marker.group(0)!r}"]
    infinitive = _TO_INFINITIVE.match(sentence, _skip_space(sentence, first.end))
    if infinitive is not None:
        # "notify a Patrol Supervisor to take the officer's location". The supervisor is who was
        # told, not what was told, and reporting the supervisor as the governed object states
        # that an agency transmits a person. This is the recipient/message confusion the of- and
        # that-rules exist to prevent, reached through a shape they do not cover — and it arrived
        # as a *complete* decomposition, which is worse than any refusal.
        #
        # The infinitive is not read as the message either, because the verb decides what it is
        # and the two readings are not distinguishable here: in "notify the supervisor to take
        # the location" the clause is what was communicated, and in "contact the desk to obtain a
        # copy" the same shape is why the actor made contact. Absent beats guessed.
        return None, first, [f"to_infinitive_after_recipient:{infinitive.group('verb')!r}"]
    marker = _CONTENT_MARKER.match(sentence, _skip_space(sentence, first.end))
    if marker is None:
        return first, None, [f"object:{first.rule}"]
    second = _message(sentence, marker, rule=f"after_{marker.group(0).lower()}")
    if second is None:
        # "advise the dispatcher of" with nothing after it states no content.
        return None, first, [f"content_marker_without_object:{marker.group(0)!r}"]
    if marker.group(0).lower() == "of" and not _DETERMINED.match(second.text) and not ACTOR.search(first.text):
        return None, None, [f"ambiguous_of_phrase:{first.text!r}+{second.text!r}"]
    return second, first, [f"recipient_then_content:{marker.group(0)!r}"]


def _skip_space(sentence: str, at: int) -> int:
    while at < len(sentence) and sentence[at].isspace():
        at += 1
    return at


def decompose(sentence: str) -> Decomposition:
    """Locate the actor, the communication act and what it governs. Absent beats invented."""
    evidence: list[str] = []
    modal = MODAL.search(sentence)
    if modal is None:
        return Decomposition(actor_is_implied=True, evidence=("no_modal:imperative_or_narrative",))

    actor, actor_evidence = _find_actor(sentence, modal)
    evidence += actor_evidence
    action, action_evidence = _find_action(sentence, modal.end())
    evidence += action_evidence
    if action is None:
        return Decomposition(actor=actor, evidence=tuple(evidence))

    obj, recipient, object_evidence = _find_object(sentence, action.end)
    evidence += object_evidence
    return Decomposition(
        actor=actor,
        communication_action=action,
        governed_object=obj,
        recipient=recipient,
        actor_is_implied=actor is None,
        evidence=tuple(evidence),
    )


__all__ = ["DECOMPOSITION_VERSION", "Decomposition", "Span", "decompose"]
