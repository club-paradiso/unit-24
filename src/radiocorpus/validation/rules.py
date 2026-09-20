"""Stage 8: deterministic validation of candidate facts.

A fact that fails a hard rule is marked REJECTED (kept for audit, never deleted). A fact that
passes is left UNVERIFIED here; promotion to VERIFIED happens in the assignment stage after
source quality and conflicts are known."""

from __future__ import annotations

import re
from collections import Counter

from radiocorpus.models import CodeMeaning, PhoneticLetter, ProcedureRule, ProtocolFact, StageRun
from radiocorpus.models.common import ReviewStatus, VerificationStatus
from radiocorpus.pipeline.runner import finish_run, start_run
from radiocorpus.store import Store

_CODE_OK = re.compile(r"^(10|11|12|13)-\d{1,3}[A-Z]?$|^(CODE|SIGNAL|STATUS) \d{1,3}[A-Z]?$")
_GENERIC_MEANING = re.compile(r"^(see|refer|page|section|table|figure|n/?a|none|reserved|not used|unassigned)\b", re.I)


def validate_fact(f: ProtocolFact, store: Store) -> list[str]:
    problems: list[str] = []
    if store.get_source(f.source_id) is None:
        problems.append("source_missing")
    if store.get_agency(f.agency_id) is None:
        problems.append("agency_missing")
    v = f.value
    if isinstance(v, CodeMeaning):
        if not _CODE_OK.match(v.code):
            problems.append("code_format")
        if _GENERIC_MEANING.match(v.meaning) or len(v.meaning) < 3:
            problems.append("meaning_generic")
        if re.fullmatch(r"[\d\W]+", v.meaning):
            problems.append("meaning_numeric_only")
    elif isinstance(v, PhoneticLetter):
        if not v.word.startswith(v.letter):
            problems.append("phonetic_word_letter_mismatch")
        if len(v.word) < 3:
            problems.append("phonetic_word_short")
    elif isinstance(v, ProcedureRule):
        if len(v.rule_text) < 20:
            problems.append("rule_text_short")
    if not f.excerpt:
        problems.append("excerpt_missing")
    return problems


def validate_all(store: Store) -> StageRun:
    facts = store.facts()
    run = start_run(store, "validation", str(len(facts)))
    stats: Counter[str] = Counter()
    with store.tx():
        for f in facts:
            if f.verification_status == VerificationStatus.REJECTED or f.review_status in {ReviewStatus.HUMAN_ACCEPTED, ReviewStatus.HUMAN_REJECTED}:
                stats["skipped_final"] += 1
                continue
            probs = validate_fact(f, store)
            if probs:
                store.record_fact_status(
                    f.fact_id,
                    verification_status=VerificationStatus.REJECTED,
                    review_status=ReviewStatus.NEEDS_REVIEW,
                    reason="validation: " + ",".join(probs),
                    run_id=run.run_id,
                )
                stats["rejected"] += 1
                for p in probs:
                    stats[f"problem:{p}"] += 1
            else:
                stats["passed"] += 1
    return finish_run(store, run, dict(stats))
