# ADR 0009 — a procedure is located, never inferred

**Status:** accepted (2026-09-21)

## Context

Adjudicating the four real documents produced 27 procedure candidates and 0 complete facts.
The filled worksheet showed why, and it was not a scoring problem: a procedure candidate
carried a sentence and a topic label and nothing else. Seven of the claims a procedure fact
requires — actor, communication medium, communication action, governed object, condition,
exception, context completeness — were simply not made. "Applicability scope is wrong" was
recorded without recording which part was wrong, so three sprints of parser work could not act
on it.

A rule is not a fact until it says **who** must do **what** communicative act **to what**.

## Decision

Decompose the rule sentence into those parts, and make every part a span of the sentence
itself, carrying its offsets and the rule that located it. A reviewer checks the claim by
reading the characters it came from.

Two shapes are handled and everything else fails closed:

```
<actor> <modal> <communication verb> <object>
<actor> <modal> <communication verb> <recipient> of|about|that <object>
```

The second shape carries more weight than its frequency suggests. In "advise the dispatcher of
their location" the grammatical object is the dispatcher, but the thing *communicated* is the
location; a decomposition that reports the dispatcher has recorded a different fact from the
one the document states.

Three rules govern what may be emitted:

1. **Locate, never supply.** Nothing comes from knowledge of what police procedures usually
   say. If the sentence states no actor, the actor is absent and the candidate says so.
2. **The subject is read structurally**, as the phrase before the modal, not matched against a
   list of job titles. A department's own word for its people works without that list being
   kept current, which is the same reason the phonetic parser reads alphabets structurally and
   only *describes* them against a reference.
3. **Ambiguity yields nothing.** "of" separates a recipient from a message ("the dispatcher of
   their location") and also binds a compound title ("the chief of police"). The reading is
   confirmed — a determined second phrase, or a first phrase naming a role — and where it
   cannot be, no object is emitted.

The decomposition is additive. It gates nothing: the same candidates are emitted as before,
and a test asserts it.

## Consequences

* A procedure candidate now makes 13 claims a reviewer can judge, where the previous version
  made 7 and left 6 unanswerable. The complete-fact gate becomes reachable for procedures for
  the first time.
* Measured against the plan each sentence in the randomized corpus was written from — the only
  ground truth available while the real documents are unreachable — precision and recall are
  both 1.000 over 61 rules, with 0 elements differing from their plan.
* Building it exposed a layout defect it did not cause: a revision stamp with no full stop was
  being merged into the sentence below it, so the subject of a rule came out as
  "Revision Date: 10-11-19 … Units". Fixed at the layout layer, with a date guard in the
  decomposition as well, because a date is never part of who must act.
* Fail-closed costs coverage. "advise dispatch of traffic" yields no object, because
  "dispatch" is not in the generic role vocabulary and "traffic" carries no determiner. That
  is the intended direction: a missing object costs a fact, a wrong one asserts something
  about an agency that the document does not say.
* None of this is evidence about a real document. Every sentence measured was generated here.
