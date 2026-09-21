"""A randomized layout corpus whose ground truth comes from the generation plan.

The nine hand-written fixtures are weak external evidence: the same author wrote the parsers
and the fixtures, so a perfect score partly measures how well the fixtures were aimed. This
module answers a narrower but harder question — *does the layout stack survive geometry it has
never seen?* — by generating documents from a seeded plan and scoring the parsers against that
plan rather than against a transcription of their own output.

Three properties keep this from becoming another self-fulfilling fixture:

* **The plan is the truth.** Column count, gutter width, every code/meaning pair and every
  decoy is decided before any parser runs. Nothing is read back from a candidate.
* **The vocabulary is fictional and generated.** No wording is copied from any real document,
  and the meanings are assembled from a neutral word list, so no parser can be matching on
  remembered phrasing.
* **The directions are not symmetric.** Losing a column is conservative and is recorded as
  such; *inventing* one corrupts every line on the page and is recorded as a defect. The same
  asymmetry governs the decoys: a date emitted as a code is a defect, never a near miss.

Recall here is meaningful only because the corpus is exhaustively known by construction. It
says nothing about real documents, which remain unretrieved.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from radiocorpus.evaluation.pdfwrite import pdf, text_width, wrap_exact
from radiocorpus.extraction.codes import parse_codes
from radiocorpus.extraction.phonetics import parse_phonetics
from radiocorpus.extraction.procedures import parse_procedures
from radiocorpus.layout.backends import layout_for

PAGE_W, PAGE_H = 612, 792
MARGIN = 40.0

# Neutral, invented vocabulary. Deliberately not radio jargon copied from any source.
_SUBJECTS = ("unit", "vehicle", "package", "signal", "channel", "relay", "marker", "beacon", "circuit", "post")
_STATES = ("clear", "busy", "standing by", "en route", "delayed", "unavailable", "restored", "holding", "released", "acknowledged")
_QUALIFIERS = ("at the north gate", "on the secondary loop", "pending confirmation", "for the second shift", "until further notice",
               "after the relay check", "with the duty supervisor", "on the alternate channel")
_LETTER_WORDS = ("ANCHOR", "BRIDGE", "CANYON", "DELTA", "EMBER", "FALCON", "GRANITE", "HARBOR", "IVORY", "JUNIPER",
                 "KESTREL", "LANTERN", "MERIDIAN", "NECTAR", "ORCHARD", "PRISM", "QUARRY", "RIVER", "SUMMIT", "TIMBER",
                 "UMBER", "VESSEL", "WILLOW", "XENON", "YARROW", "ZEPHYR")
_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

#: Radio rules written as parts, so the corpus knows who must do what to what before any
#: parser runs. A decomposition scored against a sentence the scorer itself read back would
#: measure nothing; scored against the plan that produced the sentence, it measures the parser.
_RADIO_RULES = (
    {"actor": "Members", "modal": "will", "action": "advise",
     "recipient": "the dispatcher", "marker": "of", "object": "their {subject} report",
     "tail": "over the radio before leaving the assignment"},
    {"actor": "The dispatcher", "modal": "will", "action": "repeat",
     "recipient": None, "marker": None, "object": "the assignment",
     "tail": "on the radio when a member requests it"},
    {"actor": "Units", "modal": "shall", "action": "acknowledge",
     "recipient": None, "marker": None, "object": "the radio transmission",
     "tail": "by unit number"},
    {"actor": "Assigned units", "modal": "shall", "action": "transmit",
     "recipient": None, "marker": None, "object": "the {subject} description",
     "tail": "on the assigned radio channel"},
    {"actor": "Members", "modal": "must", "action": "notify",
     "recipient": "the communications center", "marker": "of", "object": "any emergency traffic",
     "tail": "on the primary radio channel"},
)
# Paperwork, property and records wording: superficially similar verbs, no radio act at all.
_NON_RADIO_SENTENCES = (
    "The report will be forwarded to the unit secretary, who will make one copy for the unit file.",
    "A copy will be retained in the unit files in accordance with existing records-retention requirements.",
    "Members must have the {subject} recorded on the property receipt before the operator removes it.",
    "The commanding officer will file the original with the records unit at the end of the tour.",
    "Supplies will be delivered to the district and signed for by the receiving supervisor.",
)

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip().casefold()


@dataclass(frozen=True)
class StressPlan:
    """Everything decided before a parser runs. This, and only this, is the truth."""

    seed: int
    kind: str  # code_table | alphabet | narrative
    arrangement: str  # paired_columns | inline_series | single_stream | n/a
    n_columns: int
    gutter_pt: float
    column_width: float
    font_size: float
    leading: float
    n_pages: int
    furniture: bool
    heading: bool
    codes: tuple[tuple[str, str], ...] = ()
    letters: tuple[tuple[str, str], ...] = ()
    radio_sentences: tuple[str, ...] = ()
    #: One ``{actor, action, object}`` per radio sentence, decided before rendering.
    radio_parts: tuple[tuple[tuple[str, str], ...], ...] = ()
    non_radio_sentences: tuple[str, ...] = ()
    forbidden_codes: tuple[str, ...] = ()
    forbidden_letters: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------- planning


def _code_token(rng: random.Random, used: set[str]) -> str:
    while True:
        prefix = rng.choice(("10", "11", "12", "13"))
        number = rng.randint(1, 99)
        suffix = rng.choice(("", "", "", "A", "B", "F"))
        token = f"{prefix}-{number}{suffix}"
        if token not in used:
            used.add(token)
            return token


def _meaning(rng: random.Random, *, long: bool) -> str:
    base = f"{rng.choice(_SUBJECTS)} {rng.choice(_STATES)}".capitalize()
    if long:
        base = f"{base} {rng.choice(_QUALIFIERS)} {rng.choice(_QUALIFIERS)}"
    return _WS.sub(" ", base).strip()


def _decoy_dates(rng: random.Random, n: int) -> tuple[str, ...]:
    """Dates deliberately shaped like codes: the month field is drawn from 09-13."""
    out = []
    for _ in range(n):
        month = rng.choice(("09", "10", "11", "12", "13"))
        out.append(f"{month}-{rng.randint(10, 28):02d}-{rng.randint(10, 24):02d}")
    return tuple(out)


def plan(seed: int) -> StressPlan:
    """Draw one document plan. Same seed, same plan, forever."""
    rng = random.Random(seed)
    kind = rng.choice(("code_table", "code_table", "alphabet", "narrative"))
    n_columns = rng.choice((1, 2, 2, 3, 4)) if kind == "code_table" else rng.choice((1, 1, 2))
    gutter = float(rng.choice((6, 9, 12, 14, 18, 24, 30, 40)))
    font_size = float(rng.choice((7, 8, 8, 9, 10)))
    leading = font_size + rng.choice((2.0, 3.0, 4.0))
    usable = PAGE_W - 2 * MARGIN
    column_width = max(50.0, (usable - gutter * (n_columns - 1)) / n_columns)
    furniture = rng.random() < 0.5
    heading = rng.random() < 0.6
    n_pages = rng.choice((1, 1, 2, 3)) if furniture else rng.choice((1, 1, 2))

    codes: tuple[tuple[str, str], ...] = ()
    letters: tuple[tuple[str, str], ...] = ()
    arrangement = "n/a"
    forbidden_letters: tuple[str, ...] = ()
    if kind == "code_table":
        arrangement = "paired_columns" if (n_columns >= 2 and rng.random() < 0.5) else "inline_series"
        used: set[str] = set()
        per_column = rng.randint(4, 9)
        lanes = 1 if arrangement == "paired_columns" else n_columns
        pairs = []
        for _ in range(per_column * lanes):
            token = _code_token(rng, used)
            # A long meaning wraps inside its column, so its remainder lands on the next line.
            pairs.append((token, _meaning(rng, long=rng.random() < 0.35)))
        codes = tuple(pairs)
    elif kind == "alphabet":
        arrangement = "single_stream"
        letters = tuple(zip(_ALPHABET, _LETTER_WORDS, strict=True))
        forbidden_letters = ()

    radio: tuple[str, ...] = ()
    radio_parts: tuple[tuple[tuple[str, str], ...], ...] = ()
    if kind == "narrative":
        chosen = rng.sample(_RADIO_RULES, k=rng.randint(1, 3))
        rendered = [render_rule(rule, rng.choice(_SUBJECTS)) for rule in chosen]
        radio = tuple(text for text, _ in rendered)
        radio_parts = tuple(tuple(sorted(parts.items())) for _, parts in rendered)
    non_radio = tuple(rng.sample(_NON_RADIO_SENTENCES, k=rng.randint(1, 3))) if kind == "narrative" else ()

    return StressPlan(
        seed=seed,
        kind=kind,
        arrangement=arrangement,
        n_columns=n_columns,
        gutter_pt=gutter,
        column_width=column_width,
        font_size=font_size,
        leading=leading,
        n_pages=n_pages,
        furniture=furniture,
        heading=heading,
        codes=codes,
        letters=letters,
        radio_sentences=radio,
        radio_parts=radio_parts,
        non_radio_sentences=non_radio,
        forbidden_codes=_decoy_dates(rng, rng.randint(2, 4)),
        forbidden_letters=forbidden_letters,
        notes=(f"{kind}/{arrangement}", f"gutter={gutter}pt", f"columns={n_columns}"),
    )


# ---------------------------------------------------------------- rendering


def _column_x(p: StressPlan, index: int) -> float:
    return MARGIN + index * (p.column_width + p.gutter_pt)


def _fill(sentence: str, rng: random.Random) -> str:
    return sentence.format(subject=rng.choice(_SUBJECTS), qualifier=rng.choice(_QUALIFIERS))


def render_rule(rule: dict, subject: str) -> tuple[str, dict]:
    """Write one radio rule out, and return it with the parts it was written from."""
    obj = rule["object"].format(subject=subject)
    middle = f"{rule['recipient']} {rule['marker']} {obj}" if rule["recipient"] else obj
    sentence = f"{rule['actor']} {rule['modal']} {rule['action']} {middle} {rule['tail']}.".strip()
    return sentence, {"actor": rule["actor"], "action": rule["action"], "object": obj}


def render(p: StressPlan) -> bytes:
    """Lay the plan out at absolute coordinates and return a PDF."""
    rng = random.Random(p.seed ^ 0x5F5E1)
    pages: list[list[tuple]] = []
    top = PAGE_H - 70.0

    for page_index in range(p.n_pages):
        runs: list[tuple] = []
        if p.furniture:
            runs.append((MARGIN, PAGE_H - 26, 8, "EXAMPLE AGENCY - INTERNAL REFERENCE - SYNTHETIC"))
            runs.append((MARGIN, 40, 8, f"Page {page_index + 1} of {p.n_pages}"))
        if page_index == 0:
            if p.heading and p.kind == "code_table":
                runs.append((MARGIN, PAGE_H - 52, 11, "RADIO CODES", "bold"))
            elif p.heading and p.kind == "alphabet":
                runs.append((MARGIN, PAGE_H - 52, 11, "PHONETIC ALPHABET", "bold"))
            elif p.heading:
                runs.append((MARGIN, PAGE_H - 52, 11, "COMMUNICATIONS PROCEDURES", "bold"))

        if page_index == 0 and p.forbidden_codes:
            # Revision stamps live where real ones do: above the body, under a date label.
            y = PAGE_H - 66
            runs.append((MARGIN, y, 8, "Revision Date: " + "   ".join(p.forbidden_codes)))

        body_top = top - (18 if (page_index == 0 and p.forbidden_codes) else 0)
        if p.kind == "code_table":
            runs += _render_codes(p, body_top, page_index)
        elif p.kind == "alphabet":
            runs += _render_alphabet(p, body_top, page_index)
        else:
            runs += _render_narrative(p, body_top, page_index, rng)
        pages.append(runs)
    return pdf(pages, width=PAGE_W, height=PAGE_H)


def _render_codes(p: StressPlan, top: float, page_index: int) -> list[tuple]:
    if page_index > 0:
        return [(MARGIN, top, p.font_size, "Continued from the previous page.")]
    runs: list[tuple] = []
    if p.arrangement == "paired_columns":
        # column 0 holds the bare code, column 1 holds the meaning: a true two-cell row.
        y = top
        for token, meaning in p.codes:
            runs.append((_column_x(p, 0), y, p.font_size, token))
            lines = wrap_exact(meaning, p.font_size, p.column_width)
            for offset, line in enumerate(lines):
                runs.append((_column_x(p, 1), y - offset * p.leading, p.font_size, line))
            y -= p.leading * max(1, len(lines))
        return runs
    # inline_series: "CODE meaning" repeated down each column
    lanes = max(1, p.n_columns)
    per_lane = len(p.codes) // lanes or 1
    for lane in range(lanes):
        chunk = p.codes[lane * per_lane : (lane + 1) * per_lane]
        y = top
        for token, meaning in chunk:
            for line in wrap_exact(f"{token} {meaning}", p.font_size, p.column_width):
                runs.append((_column_x(p, lane), y, p.font_size, line))
                y -= p.leading
    return runs


def _render_alphabet(p: StressPlan, top: float, page_index: int) -> list[tuple]:
    if page_index > 0:
        return [(MARGIN, top, p.font_size, "Continued from the previous page.")]
    runs: list[tuple] = []
    per_column = -(-len(p.letters) // max(1, p.n_columns))
    for i, (letter, word) in enumerate(p.letters):
        lane = i // per_column
        y = top - (i % per_column) * p.leading
        runs.append((_column_x(p, lane), y, p.font_size, f"{letter} {word}"))
    return runs


def _render_narrative(p: StressPlan, top: float, page_index: int, rng: random.Random) -> list[tuple]:
    runs: list[tuple] = []
    y = top
    sentences = list(p.radio_sentences) + list(p.non_radio_sentences)
    rng.shuffle(sentences)
    for sentence in sentences:
        for line in wrap_exact(_fill(sentence, rng), p.font_size, p.column_width):
            runs.append((_column_x(p, 0), y, p.font_size, line))
            y -= p.leading
        y -= p.leading * 0.5
    if page_index > 0 and not runs:
        runs.append((MARGIN, top, p.font_size, "Continued from the previous page."))
    return runs


# ---------------------------------------------------------------- scoring


def plan_overflow(p: StressPlan) -> list[str]:
    """Body lines the plan would place outside their own column.

    The generator must not emit geometry no document has. If a line overflows its column, the
    columns overlap, and any column-detection score taken from that page measures the
    generator's arithmetic rather than the parser. This must always be empty.
    """
    bad: list[str] = []
    for _, meaning in p.codes:
        text = meaning if p.arrangement == "paired_columns" else f"XX-00 {meaning}"
        for line in wrap_exact(text, p.font_size, p.column_width):
            if text_width(line, p.font_size) > p.column_width + 0.01:
                bad.append(line)
    for letter, word in p.letters:
        line = f"{letter} {word}"
        if text_width(line, p.font_size) > p.column_width + 0.01:
            bad.append(line)
    return bad


@dataclass
class StressResult:
    seed: int
    kind: str
    arrangement: str
    planned_columns: int
    detected_columns: int
    gutter_pt: float
    column_verdict: str  # exact | conservative_merge | invented_columns
    code_tp: int = 0
    code_fp: int = 0
    code_fn: int = 0
    letter_tp: int = 0
    letter_fp: int = 0
    letter_fn: int = 0
    decoy_emitted: tuple[str, ...] = ()
    procedures_emitted: int = 0
    procedure_false_positive: bool = False
    decomposition_tp: int = 0
    decomposition_fp: int = 0
    decomposition_fn: int = 0
    decomposition_complete: int = 0
    decomposition_scored: int = 0
    plan_overflow_lines: int = 0
    layout_error: str | None = None

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["decoy_emitted"] = list(self.decoy_emitted)
        return d


def evaluate(p: StressPlan) -> StressResult:
    """Score one plan. Every comparison is plan-versus-output; nothing is read back."""
    data = render(p)
    try:
        layout = layout_for(data, "application/pdf")
    except Exception as error:  # a layout failure is a result, not an exception to hide
        return StressResult(p.seed, p.kind, p.arrangement, p.n_columns, 0, p.gutter_pt, "layout_error",
                            layout_error=f"{type(error).__name__}: {error}")

    detected = max((page.column_count for page in layout.pages), default=1)
    if detected == p.n_columns:
        verdict = "exact"
    elif detected < p.n_columns:
        verdict = "conservative_merge"
    else:
        verdict = "invented_columns"

    result = StressResult(p.seed, p.kind, p.arrangement, p.n_columns, detected, p.gutter_pt, verdict)
    result.plan_overflow_lines = len(plan_overflow(p))

    codes = parse_codes(layout)
    got = {c.code: _norm(c.meaning) for c in codes}
    want = {code: _norm(meaning) for code, meaning in p.codes}
    result.code_tp = sum(1 for k, v in want.items() if got.get(k) == v)
    result.code_fn = len(want) - result.code_tp
    result.code_fp = sum(1 for k, v in got.items() if want.get(k) != v)

    # A decoy counts as emitted only when the candidate actually came from the date line.
    # A planned code may legitimately coincide with a fragment of a decoy ("10-22" inside
    # "10-10-22"); scoring that as a defect would manufacture failures that did not happen.
    planned = {code for code, _ in p.codes}
    decoys = set()
    for date in p.forbidden_codes:
        for c in codes:
            if c.code.replace(" ", "") not in planned and date in c.excerpt:
                decoys.add(date)
    result.decoy_emitted = tuple(sorted(decoys))

    letters = parse_phonetics(layout)
    got_l = {x.letter: x.word.upper() for x in letters}
    want_l = {letter: word for letter, word in p.letters}
    result.letter_tp = sum(1 for k, v in want_l.items() if got_l.get(k) == v)
    result.letter_fn = len(want_l) - result.letter_tp
    result.letter_fp = sum(1 for k, v in got_l.items() if want_l.get(k) != v)

    procedures = parse_procedures(layout)
    result.procedures_emitted = len(procedures)
    _score_decomposition(p, procedures, result)
    # The only procedure claim this corpus can adjudicate: a page with no radio act at all
    # must yield nothing. What the parser *calls* a rule it does find is not scored here.
    result.procedure_false_positive = bool(procedures) and not p.radio_sentences
    return result


def _score_decomposition(p: StressPlan, procedures, result: StressResult) -> None:
    """Compare the located parts with the parts the sentence was written from.

    Only sentences the parser actually emitted are scored, and each is matched to its plan by
    the object phrase it was built around, so a decomposition is never compared with a rule it
    did not come from. An element the plan states and the parser did not locate is a miss; an
    element that differs from the plan is a false part, which is the direction that matters.
    """
    planned = [dict(parts) for parts in p.radio_parts]
    if not planned:
        return
    for candidate in procedures:
        parts = candidate.decomposition
        if parts is None:
            continue
        text = _norm(candidate.rule_text)
        match = next((q for q in planned if _norm(q["object"]) in text and _norm(q["action"]) in text), None)
        if match is None:
            continue
        result.decomposition_scored += 1
        if parts.complete:
            result.decomposition_complete += 1
        for key, span in (("actor", parts.actor), ("action", parts.communication_action),
                          ("object", parts.governed_object)):
            want = _norm(match[key])
            if span is None:
                result.decomposition_fn += 1
            elif _norm(span.text) == want:
                result.decomposition_tp += 1
            else:
                result.decomposition_fp += 1


def run(seeds: range | list[int]) -> tuple[list[StressResult], dict]:
    results = [evaluate(plan(s)) for s in seeds]
    return results, summarise(results)


def summarise(results: list[StressResult]) -> dict:
    total = len(results)
    by_verdict: dict[str, int] = {}
    for r in results:
        by_verdict[r.column_verdict] = by_verdict.get(r.column_verdict, 0) + 1
    code_tp = sum(r.code_tp for r in results)
    code_fp = sum(r.code_fp for r in results)
    code_fn = sum(r.code_fn for r in results)
    let_tp = sum(r.letter_tp for r in results)
    let_fp = sum(r.letter_fp for r in results)
    let_fn = sum(r.letter_fn for r in results)

    def pr(tp: int, fp: int, fn: int) -> dict:
        return {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "recall": round(tp / (tp + fn), 4) if tp + fn else None,
        }

    gutters: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = gutters.setdefault(f"{r.gutter_pt:g}", {})
        bucket[r.column_verdict] = bucket.get(r.column_verdict, 0) + 1

    return {
        "documents": total,
        "column_detection": by_verdict,
        "column_detection_by_gutter_pt": dict(sorted(gutters.items(), key=lambda kv: float(kv[0]))),
        "invented_columns": by_verdict.get("invented_columns", 0),
        "code_meaning": pr(code_tp, code_fp, code_fn),
        "phonetic_letter": pr(let_tp, let_fp, let_fn),
        "decoy_dates_emitted_as_codes": sum(len(r.decoy_emitted) for r in results),
        "documents_emitting_a_decoy": sum(1 for r in results if r.decoy_emitted),
        "procedure_false_positive_documents": sum(1 for r in results if r.procedure_false_positive),
        "procedure_candidates_emitted": sum(r.procedures_emitted for r in results),
        "procedure_decomposition": {
            **pr(sum(r.decomposition_tp for r in results), sum(r.decomposition_fp for r in results),
                 sum(r.decomposition_fn for r in results)),
            "rules_scored": sum(r.decomposition_scored for r in results),
            "rules_fully_decomposed": sum(r.decomposition_complete for r in results),
            "note": "actor, communication action and governed object, against the plan each sentence was written from",
        },
        "layout_errors": sum(1 for r in results if r.layout_error),
        "plans_overflowing_their_columns": sum(1 for r in results if r.plan_overflow_lines),
    }


__all__ = ["StressPlan", "StressResult", "evaluate", "plan", "plan_overflow", "render", "run", "summarise"]
