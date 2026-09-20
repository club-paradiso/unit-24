"""Replay audited candidates through the current parsers.

The four real validation documents are not retrievable in this environment, so the corpus
cannot be re-parsed end to end. What *is* committed is the previous parser's actual output on
those documents (``data/audit/real_facts.jsonl``) together with an independent review of it.
Replay feeds each recorded excerpt back through the current parsers and asks whether the same
claim is still made.

What replay does and does not establish:

* **Rejection of a labelled false positive is real evidence.** The excerpt is the exact text
  the old parser saw; refusing it now is a genuine precision gain that does not depend on
  geometry we no longer have.
* **Retention of a labelled true fact is a lower bound**, not recall. A parser that needs
  structure may legitimately decline a flattened excerpt and still recover the fact from the
  real page.
* **Nothing here measures recall on real documents.** False negatives cannot be enumerated
  without the documents.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from radiocorpus.evaluation.gold import GoldRecord, Label
from radiocorpus.extraction.codes import parse_code_blocks
from radiocorpus.extraction.phonetics import parse_phonetic_blocks
from radiocorpus.extraction.procedures import parse_procedure_blocks
from radiocorpus.extraction.text import TextBlock

ISOLATED = "isolated_excerpt"
PAGE_GROUP = "page_group_reconstruction"


@dataclass
class ReplayOutcome:
    gold_id: str
    fact_id: str
    document_key: str
    fact_type: str
    key: str
    label: str
    failure_class: str
    reemitted: bool
    match_detail: str
    context_complete: bool | None = None
    structural_reason: str | None = None
    replay_mode: str = ISOLATED
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gold_id": self.gold_id,
            "fact_id": self.fact_id,
            "document_key": self.document_key,
            "fact_type": self.fact_type,
            "key": self.key,
            "label": self.label,
            "failure_class": self.failure_class,
            "reemitted": self.reemitted,
            "match_detail": self.match_detail,
            "context_complete": self.context_complete,
            "structural_reason": self.structural_reason,
            "replay_mode": self.replay_mode,
            "notes": list(self.notes),
        }


def _replay_code(gold: GoldRecord) -> tuple[bool, str, str | None, bool | None]:
    want_code = str(gold.expected_value.get("code", "")).upper()
    for c in parse_code_blocks([TextBlock(gold.locator, gold.excerpt)]):
        if c.code.upper() == want_code:
            return True, f"code={c.code} meaning={c.meaning!r}", c.structural_reason, None
    return False, "no code candidate re-emitted for this excerpt", None, None


def _replay_phonetic(gold: GoldRecord) -> tuple[bool, str, str | None, bool | None]:
    want = str(gold.expected_value.get("letter", "")).upper()
    for c in parse_phonetic_blocks([TextBlock(gold.locator, gold.excerpt)]):
        if c.letter == want:
            return True, f"letter={c.letter} word={c.word!r}", c.structural_reason, None
    return False, "no phonetic mapping re-emitted for this excerpt", None, None


def _replay_procedure(gold: GoldRecord) -> tuple[bool, str, str | None, bool | None]:
    want = str(gold.expected_value.get("procedure", ""))
    text = str(gold.expected_value.get("rule_text") or gold.excerpt)
    for c in parse_procedure_blocks([TextBlock(gold.locator, text)]):
        if c.procedure == want:
            return True, f"procedure={c.procedure} medium={c.medium}", c.structural_reason, c.context_complete
    return False, "no procedure candidate re-emitted for this excerpt", None, None


_REPLAYERS = {
    "code_meaning": _replay_code,
    "phonetic_letter": _replay_phonetic,
    "procedure_rule": _replay_procedure,
}


def replay_page_groups(gold_records: list[GoldRecord]) -> list[ReplayOutcome]:
    """Replay with every audited excerpt from one page presented together.

    An isolated excerpt carries no structural evidence at all, so a structure-gated parser
    refuses it by design. Grouping a page's excerpts back into consecutive lines restores the
    one signal that a flat text file can legitimately carry — a run of records that each open
    with a code, or a run of distinct letter pairs — while still supplying no geometry. The
    gap between this mode and the fixture results is exactly the part of the problem that only
    coordinates can solve.
    """
    groups: dict[tuple[str, str], list[GoldRecord]] = {}
    for g in gold_records:
        groups.setdefault((g.source_id, g.locator), []).append(g)
    outcomes: list[ReplayOutcome] = []
    for (_source, locator), members in sorted(groups.items()):
        text = "\n".join(dict.fromkeys(m.excerpt for m in members if m.excerpt))
        codes = {c.code.upper(): c for c in parse_code_blocks([TextBlock(locator, text)])}
        letters = {c.letter: c for c in parse_phonetic_blocks([TextBlock(locator, text)])}
        proc_text = "\n".join(dict.fromkeys(str(m.expected_value.get("rule_text") or m.excerpt) for m in members))
        procs = parse_procedure_blocks([TextBlock(locator, proc_text)])
        for g in members:
            hit, detail, reason, complete = False, "not re-emitted in page-group mode", None, None
            if g.fact_type == "code_meaning":
                want = str(g.expected_value.get("code", "")).upper()
                c = codes.get(want)
                if c is not None:
                    expected_meaning = str(g.expected_value.get("meaning", ""))
                    same = c.meaning.strip().lower() == expected_meaning.strip().lower()
                    hit, reason = True, c.structural_reason
                    detail = f"code={c.code} meaning={c.meaning!r} same_as_baseline={same}"
            elif g.fact_type == "phonetic_letter":
                want = str(g.expected_value.get("letter", "")).upper()
                c = letters.get(want)
                if c is not None:
                    hit, reason, detail = True, c.structural_reason, f"letter={c.letter} word={c.word!r}"
            elif g.fact_type == "procedure_rule":
                want = str(g.expected_value.get("procedure", ""))
                for c in procs:
                    if c.procedure == want:
                        hit, reason, complete = True, c.structural_reason, c.context_complete
                        detail = f"procedure={c.procedure} medium={c.medium}"
                        break
            notes: list[str] = []
            if g.label == Label.TRUE_FACT and not hit:
                notes.append("retention_loss_without_geometry")
            if g.label in (Label.FALSE_POSITIVE, Label.INSUFFICIENT_CONTEXT) and not hit:
                notes.append("false_positive_eliminated")
            if g.label in (Label.FALSE_POSITIVE, Label.INSUFFICIENT_CONTEXT) and hit:
                notes.append("requires_geometry: flattened text cannot separate adjacent columns")
            outcomes.append(
                ReplayOutcome(
                    gold_id=g.gold_id, fact_id=g.fact_id, document_key=g.document_key, fact_type=g.fact_type,
                    key=g.key, label=g.label, failure_class=g.failure_class, reemitted=hit, match_detail=detail,
                    context_complete=complete, structural_reason=reason, replay_mode=PAGE_GROUP, notes=notes,
                )
            )
    outcomes.sort(key=lambda o: o.gold_id)
    return outcomes


def replay(gold_records: list[GoldRecord]) -> list[ReplayOutcome]:
    outcomes: list[ReplayOutcome] = []
    for g in gold_records:
        fn = _REPLAYERS.get(g.fact_type)
        if fn is None:
            outcomes.append(
                ReplayOutcome(
                    gold_id=g.gold_id,
                    fact_id=g.fact_id,
                    document_key=g.document_key,
                    fact_type=g.fact_type,
                    key=g.key,
                    label=g.label,
                    failure_class=g.failure_class,
                    reemitted=False,
                    match_detail="fact type has no replay path",
                    notes=["unsupported_fact_type"],
                )
            )
            continue
        hit, detail, reason, complete = fn(g)
        notes: list[str] = []
        if g.label == Label.TRUE_FACT and not hit:
            notes.append("retention_loss_text_only: may still be recoverable from real page geometry")
        if g.label in (Label.FALSE_POSITIVE, Label.INSUFFICIENT_CONTEXT) and not hit:
            notes.append("false_positive_eliminated")
        outcomes.append(
            ReplayOutcome(
                gold_id=g.gold_id,
                fact_id=g.fact_id,
                document_key=g.document_key,
                fact_type=g.fact_type,
                key=g.key,
                label=g.label,
                failure_class=g.failure_class,
                reemitted=hit,
                match_detail=detail,
                context_complete=complete,
                structural_reason=reason,
                notes=notes,
            )
        )
    return outcomes
