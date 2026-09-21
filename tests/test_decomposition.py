"""Tests for procedure decomposition.

A decomposition turns a sentence into a claim about who must do what. The dangerous failure
is not an empty field — it is a confidently wrong one, because a wrong actor is a false
statement about which people an agency directs. Most of these tests therefore assert that an
element is *absent* where the sentence does not clearly state it.
"""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

from radiocorpus.evaluation.gold import audit_lines
from radiocorpus.evaluation.stress import plan, render
from radiocorpus.evaluation.stress import run as stress_run
from radiocorpus.extraction.decomposition import decompose
from radiocorpus.extraction.procedures import parse_procedures
from radiocorpus.layout.backends import layout_for

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "data" / "evaluation" / "decomposition_refusal_review.json"


def _real_rule_sentences() -> list[str]:
    """The verbatim rule sentences the coverage probe measures, read the same way it reads them."""
    seen: list[str] = []
    for line in audit_lines(ROOT / "data" / "audit" / "real_facts.jsonl"):
        fact = json.loads(line)
        if fact["fact_type"] != "procedure_rule":
            continue
        text = (fact["value"].get("rule_text") or fact.get("excerpt") or "").strip()
        if text and text not in seen:
            seen.append(text)
    return seen


def _parts(sentence: str) -> tuple[str | None, str | None, str | None]:
    d = decompose(sentence)
    return (
        d.actor.text if d.actor else None,
        d.communication_action.text if d.communication_action else None,
        d.governed_object.text if d.governed_object else None,
    )


# ---------------------------------------------------------------- the shapes it handles


def test_simple_directive():
    assert _parts("Units will acknowledge the radio transmission by unit number.") == (
        "Units", "acknowledge", "the radio transmission",
    )


def test_the_recipient_is_not_the_message():
    """The grammatical object is the dispatcher; the thing communicated is the location.

    Reporting the dispatcher as the governed object would record the wrong fact, and the
    first version of this parser did exactly that.
    """
    actor, action, obj = _parts("Members shall advise the dispatcher of their location.")
    assert (actor, action, obj) == ("Members", "advise", "their location")
    assert decompose("Members shall advise the dispatcher of their location.").recipient.text == "the dispatcher"


def test_a_that_clause_is_the_message():
    assert _parts("Officers shall advise the dispatcher that they are en route.")[2] == "they are en route"


def test_a_leading_condition_is_stepped_over_to_reach_the_subject():
    actor, _, _ = _parts("When a unit is dispatched, members shall advise the dispatcher of their location.")
    assert actor == "members"


def test_an_unfamiliar_role_still_yields_an_actor():
    """The subject is read structurally, so an agency's own word for its people works.

    A list of job titles would have to be kept current for every department in the country;
    the position before the modal does not.
    """
    actor, _, _ = _parts("Telecommunicators assigned to the north console shall repeat the assignment.")
    assert actor == "Telecommunicators assigned to the north console"


def test_spans_address_the_characters_they_quote():
    sentence = "Members shall advise the dispatcher of their location."
    d = decompose(sentence)
    for span in (d.actor, d.communication_action, d.governed_object, d.recipient):
        assert sentence[span.start : span.end] == span.text


# ---------------------------------------------------------------- what it refuses


def test_no_modal_means_no_decomposition():
    """An imperative names no actor, and an implied one is not a stated one."""
    d = decompose("Upon completing the assignment, return to service on the primary channel.")
    assert d.actor is None and d.actor_is_implied
    assert not d.complete


def test_a_nearer_non_communication_verb_blocks_the_act():
    """"shall take the location and report it" is governed by take, not by report."""
    d = decompose("Members shall take the officer's location and report it later.")
    assert d.communication_action is None
    assert any("nearer_non_communication_verb" in e for e in d.evidence)


def test_a_non_communication_rule_yields_no_act():
    d = decompose("A copy will be retained in the unit files in accordance with existing requirements.")
    assert d.communication_action is None and not d.complete


def test_an_ambiguous_of_phrase_yields_no_object():
    """"the chief of police" is a title; "the dispatcher of their location" is a message.

    Without a way to tell them apart the object is left absent, because a wrong object is a
    false fact and a missing one is only a gap.
    """
    d = decompose("Members shall advise the chief of police of the incident.")
    assert d.governed_object is None
    assert any("ambiguous_of_phrase" in e for e in d.evidence)


def test_a_content_marker_with_nothing_after_it_states_no_message():
    d = decompose("Members will advise the dispatcher of.")
    assert d.governed_object is None and not d.complete


def test_a_revision_stamp_is_never_the_actor():
    """A stamp glued onto the front of a sentence must not become the people it directs."""
    d = decompose("Revision Date: 10-11-19 12-03-21 Units shall acknowledge the radio transmission.")
    assert d.actor is not None
    assert d.actor.text == "Units"
    assert "dropped_leading_date_stamp" in d.evidence


# ---------------------------------------------------------------- measured, not asserted


def test_decomposition_matches_the_plan_each_sentence_was_written_from():
    """Ground truth is the plan, not a reading of the parser's own output."""
    _, summary = stress_run(range(1, 121))
    d = summary["procedure_decomposition"]
    assert d["rules_scored"] > 0
    assert d["fp"] == 0, "a located element differed from the plan it was written from"
    assert d["precision"] == 1.0
    assert d["recall"] == 1.0


def test_a_stamp_line_is_not_merged_into_the_sentence_below_it():
    """The layout fix behind the actor defect, guarded at its own level."""
    document = next(p for p in (plan(s) for s in range(1, 200)) if p.kind == "narrative" and p.radio_sentences and p.forbidden_codes)
    for block in layout_for(render(document), "application/pdf").included_blocks():
        if "Revision Date:" in block.text:
            assert "shall" not in block.text and "will" not in block.text, block.text


def test_decomposition_does_not_change_which_candidates_are_emitted():
    """It is metadata about a candidate, never a gate on one.

    If adding it changed the emitted set, every earlier measurement would need re-running and
    the comparison with the audited replay would be meaningless.
    """
    candidates = []
    for seed in range(1, 200):
        document = plan(seed)
        if document.kind != "narrative" or not document.radio_sentences:
            continue
        candidates = parse_procedures(layout_for(render(document), "application/pdf"))
        if candidates:
            break
    assert candidates, "no narrative document in the corpus yielded a procedure candidate"
    assert all(c.decomposition is not None for c in candidates)
    # Every candidate still carries the gating fields the previous version decided on.
    assert all(c.medium and c.structural_reason for c in candidates)


# ---------------------------------------------------------------- found on real sentences
#
# Everything below was found by running the decomposition over verbatim sentences from the
# real corpus rather than over generated ones. The generator never produced these shapes.


def test_a_passive_does_not_make_its_patient_the_actor():
    """"The location will be relayed" does not direct the location to do anything.

    This produced a *complete* decomposition with the wrong actor, which is the worst
    outcome the instrument can have: a confident false statement about who an agency directs.
    """
    d = decompose("The location will be relayed the assigned unit.")
    assert d.actor is None
    assert "passive_voice:agent_unstated" in d.evidence
    assert not d.complete


def test_a_named_agent_in_a_passive_is_taken_when_it_reads_as_a_role():
    d = decompose("The assignment shall be broadcast by the dispatcher on the primary channel.")
    assert d.actor is not None and d.actor.text == "the dispatcher"


def test_a_by_phrase_that_names_a_means_is_not_an_agent():
    """"by radio" and "by unit number" say how, not who."""
    d = decompose("The assignment shall be broadcast by radio.")
    assert d.actor is None
    assert any("by_phrase_is_not_a_role" in e for e in d.evidence)


def test_a_recipient_marked_by_a_preposition_is_still_a_recipient():
    """From a real directive: "acknowledge **to** the dispatcher **that** …"."""
    d = decompose(
        "The assigned supervisor must acknowledge to the OEMC dispatcher "
        "that he or she is monitoring the motor vehicle pursuit."
    )
    assert d.actor.text == "The assigned supervisor"
    assert d.communication_action.text == "acknowledge"
    assert d.governed_object.text == "he or she is monitoring the motor vehicle pursuit"


def test_a_that_clause_is_not_truncated_to_a_noun_phrase():
    """Reading the clause as a phrase reported "he" as the thing communicated."""
    d = decompose("Officers shall advise the dispatcher that he or she is en route to the scene.")
    assert d.governed_object.text.startswith("he or she is en route")


def test_a_section_number_is_not_part_of_the_actor():
    """A heading number glued to a sentence is not one of the people the rule directs."""
    d = decompose("2.1 - Canadian Provinces Members shall transmit the code on the assigned channel.")
    assert d.actor is not None
    assert not d.actor.text.startswith("2.1")
    assert "dropped_leading_enumerator" in d.evidence


# ---------------------------------------------------------------- the coverage evidence itself
#
# A coverage figure whose cases are not in the repository cannot be checked and cannot be
# compared against after a repair. These guard the artifact rather than the parser.


def _reviews() -> dict:
    return json.loads(REVIEW_PATH.read_text())


def test_every_real_rule_sentence_carries_a_review():
    """A sentence the coverage figure counts but nobody looked at is an unexamined case."""
    reviewed = set(_reviews()["reviews"])
    for sentence in _real_rule_sentences():
        digest = hashlib.sha256(sentence.encode()).hexdigest()
        assert digest in reviewed, f"unreviewed sentence: {sentence[:80]!r}"


def test_a_review_addresses_the_sentence_it_is_keyed_to():
    """Keying by hash is what makes a review fall away instead of silently outliving its sentence."""
    for digest, entry in _reviews()["reviews"].items():
        assert hashlib.sha256(entry["sentence"].encode()).hexdigest() == digest


def test_the_review_is_not_ground_truth_and_says_so():
    """It is one automated reading. Counting it toward the readiness gate would be a lie."""
    payload = _reviews()
    assert payload["reviewer_is_human"] is False
    vocabulary = set(payload["classifications"])
    for entry in payload["reviews"].values():
        assert entry["classification"] in vocabulary


def test_the_review_records_defects_that_are_not_fixed():
    """The point of the artifact: known-open defects stay visible instead of dissolving into a rate."""
    classifications = collections.Counter(e["classification"] for e in _reviews()["reviews"].values())
    assert classifications["defect"] > 0
    # A refusal on a sentence that does state a directed act, and a located span that states
    # something the sentence does not, are different failures and are counted apart.
    assert "wrong" in _reviews()["classifications"]
