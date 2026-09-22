# ADR 0008 — one verdict per claim, and no metric over unjudged claims

**Status:** accepted (2026-09-21)

## Context

The independent review in `data/audit/fact_audit.jsonl` found 61 of 116 candidate meanings
supported but only 24 complete facts, and **0 of 27 procedures with correct applicability
scope**. That last number was unusable. The instrument recorded one boolean,
`applicability_scope_correct`, so a reviewer could say a procedure's scope was wrong but not
which part of it was wrong — the section it was attached to, the condition that governed it,
or the exception that qualified it. Three sprints of parser work could not act on the finding
because the finding had no shape.

The instrument was also silent on who issued a document. `source_authoritative` judges the
*source*; conflating that with the issuing authority is exactly how a mirror becomes an
official record.

And a blank field was indistinguishable from an agreed one. Any scorer reading those records
would have computed a complete-fact rate over questions nobody had been asked.

## Decision

Adjudication is a first-class artifact with one verdict per claim a candidate makes
(`src/radiocorpus/evaluation/adjudication.py`). A procedure is judged on its actor, medium,
communication action, governed object, condition, exception, section scope and context
completeness, separately; every family is judged on meaning, agency, issuing authority,
region, currentness and learner safety.

Three rules are enforced in code rather than in review discipline:

1. **`UNADJUDICATED` is the default and is never read as agreement.** A metric whose
   population contains an unadjudicated field is returned as `null` together with the count
   that blocked it.
2. **A complete fact requires every applicable claim.** Meaning support is the weakest claim a
   candidate makes; reporting it as though it were the fact is what made the earlier numbers
   look better than they were.
3. **Recall needs its own evidence.** Candidates cannot show what a document contains that the
   parser missed, so recall is computed only against a reviewer-supplied missed-fact
   inventory, and is `null` with a reason otherwise.

Verdicts from the previous review are carried forward mechanically where they answer the same
question, and left `UNADJUDICATED` where they do not. Nothing is inferred from a question that
was never asked.

## Consequences

* The gap is now measurable and it is large: of 116 candidates, **0 are fully adjudicated**,
  the issuing authority is unjudged on all 116, and the seven procedure claims are unjudged on
  all 27. The previous instrument answered 6 of 15 questions.
* Real-document complete-fact precision, complete-scope precision and recall are reported as
  `null`. This is a worse-looking result than a number would be, and it is the accurate one.
* The scorer records which parser version produced the candidates it is scoring and refuses to
  let an older parser's figures be read as the current parser's.
* Filling the worksheet in is human work. No agent verdict in this repository satisfies the
  human-acceptance gate, and the artifact says so on every record.
