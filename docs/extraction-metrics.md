# Extraction metrics and parser readiness

**Parser versions:** layout-2 (`layout_code_fingerprint` pins the source), code parser v4,
phonetic parser v5, procedure parser v4. **Baseline:** commit `7d8e838`, parser v2.

The code and phonetic parsers moved to v4 when the randomized corpus exposed three defects in
v3; the phonetic parser moved again to v5 when a real third-party PDF exposed a fourth. Facts
already extracted keep the version that produced them; provenance records what happened, it is
not rewritten.

## Readiness status

> **EXTRACTION_NOT_READY**

This is not a statement that the parser got worse. The measured improvements below are real
and reproducible. The status is NOT_READY because the evidence needed to clear the sprint's
own quality gate could not be obtained:

1. **No real document was parsed.** All four validation documents were refused by the
   organisation egress policy (HTTP 403 at CONNECT). Nothing was substituted. Precision on
   real documents is therefore unmeasured, and the ≥95% / ≥90% targets cannot be adjudicated.
2. **Complete-fact precision is 0.000 on every family, for parser v2, and unmeasured for the
   current parsers.** The filled adjudication worksheet establishes why, and it is not a
   scoring artefact: the issuing authority is absent from all 116 candidates, the reviewer
   judged 0 of 116 learner-safe, and a v2 procedure candidate never carried an actor, a
   communication action or a governed object. The parser now decomposes procedures (ADR 0009),
   so the gate is reachable — but it has been exercised only on generated sentences, and no
   real document has been through it.
3. **No OCR validation against a real scan.** The fail-closed gate is exercised against a
   synthetic image-only page — it refuses, emits nothing, and refuses again when a supplied
   OCR backend returns blank — and against a real PDF with no extractable text, which now
   warns instead of returning empty in silence. Neither is a raster scan. Every PDF in the
   execution environment was examined and none has an image-only page; no scan could be
   fetched. Recorded as explicitly unresolved in `data/evaluation/ocr_validation_status.json`.
4. **Nothing has been adjudicated by a human.** The one independent review in the corpus was
   performed by an agent and records `human_review: false` on all 116 candidates. The
   readiness gate requires human acceptance, and no artifact in this repository satisfies it.

Project status remains **NOT_READY** for nationwide discovery regardless of this sprint.

The randomized corpus and threshold sweep added below **do not change this status**. They
replace three unmeasured assertions with measurements and they found three real defects, but
every document in them is synthetic. Precision on a document nobody wrote is not precision on
a document an agency published.

## What the replay measures

The four documents are unavailable, but the previous parser's actual output on them is
committed (`data/audit/real_facts.jsonl`), as is an independent review of it
(`data/audit/fact_audit.jsonl`). Replay feeds each recorded excerpt back through the current
parsers.

* Refusing a labelled false positive **is** evidence: the excerpt is the exact text the old
  parser saw, and the refusal does not depend on geometry we no longer have.
* Retaining a labelled true fact is a **lower bound**, not recall. A structure-gated parser
  may legitimately decline a flattened excerpt and still recover the fact from the real page.
* Recall on real documents is **not measurable** here.

Two modes are reported. `isolated_excerpt` presents one flattened line with no structural
evidence. `page_group_reconstruction` regroups a page's excerpts into consecutive lines,
restoring the weakest legitimate text signal (a run of sibling records) while still supplying
no coordinates.

## Gold labels

116 records derived mechanically from the independent review, keeping the original flags, the
derivation rule and the reviewer. The audit file itself is unmodified.

| label | n |
|---|---|
| TRUE_FACT | 24 |
| WRONG_NORMALIZATION | 26 |
| WRONG_SCOPE | 11 |
| FALSE_POSITIVE | 42 |
| INSUFFICIENT_CONTEXT | 13 |

61 meaning-supported, 55 unsupported, matching the review's own totals.

## Replay results

Meaning precision over emitted candidates:

| fact family | baseline | isolated | page-group | FPs eliminated (isolated) |
|---|---|---|---|---|
| code_meaning | 0.444 (54 emitted) | — (0 emitted) | 0.708 (24 emitted) | 30 / 30 |
| phonetic_letter | 0.765 (34) | — (0) | 0.839 (31) | 8 / 8 |
| phonetic_system | 0.000 (1) | — (0) | — (0) | 1 / 1 |
| procedure_rule | **0.407** (27) | **0.900** (10) | 0.769 (13) | 15 / 16 |
| overall | 0.526 (116) | 0.900 (10) | 0.779 (68) | 54 / 55 |

Procedure precision restricted to candidates the parser marks `context_complete`: **1.000**.
The one residual false positive is correctly flagged incomplete.

Codes and phonetics emit nothing under `isolated_excerpt` by design: a lone flattened line
carries no structural evidence, so a structure-gated parser must refuse it. The cost is
visible in page-group mode, where 17 of 24 true code facts return.

### Failure classes eliminated (isolated mode)

| class | eliminated |
|---|---|
| LAYOUT_COLUMN_BLEED | 22 / 22 |
| LAYOUT_CONTINUATION_LOST | 8 / 8 |
| SEMANTIC_MISCLASSIFICATION | 9 / 9 |
| HEADING_MISREAD | 3 / 3 |
| DATE_OR_REVISION_MISREAD | 1 / 1 |
| PAGE_FURNITURE | 1 / 1 |
| CONTEXT_OMITTED | 3 / 4 |
| UNCLASSIFIED | 7 / 7 |

Every residual error in page-group mode is a layout class — column bleed or lost continuation
— which is the expected result: flattened text cannot separate adjacent columns. The fixture
results below show those same classes resolved when coordinates are present.

### Per document (page-group)

| document | audited | baseline | replay | FPs eliminated |
|---|---|---|---|---|
| CHP_AURAL_BREVITY | 85 | 0.588 | 0.782 | 23 / 35 |
| PHL_PPD_DIRECTIVE_7_1 | 15 | 0.467 | 0.750 | 6 / 8 |
| CHI_CPD_DIRECTIVE | 8 | 0.250 | 0.667 | 5 / 6 |
| IN_ISP_COMMUNICATIONS | 8 | 0.250 | 1.000 | 6 / 6 |

## Fixtures: the only place recall is valid

Nine synthetic PDFs reproduce the geometry of each real failure with invented wording. Their
ground truth is exhaustive **by construction**, which is the only reason recall is meaningful.

| family | tp | fp | fn | precision | recall |
|---|---|---|---|---|---|
| code_meaning | 14 | 0 | 0 | 1.000 | 1.000 |
| phonetic_letter | 26 | 0 | 0 | 1.000 | 1.000 |
| procedure_rule | 3 | 0 | 0 | 1.000 | 1.000 |

Failed structural checks: **0**. These include column count, forbidden code and letter
emissions, divergence preservation, and cross-page context capture.

A perfect score on nine fixtures the same author designed is weak evidence about real
documents. It is offered as a demonstration that the mechanism works when geometry exists,
not as a precision claim.

## Real-document validation

This is the sprint's primary gate, and it did not pass. What follows is what was actually
established, separated from what was not.

### Acquisition: still blocked, re-attempted and logged

All four validation documents were re-requested on 2026-09-21. Every one was refused by the
organisation egress policy with **403 at CONNECT**, and the refusal is now recorded per
document in `data/raw/layout-validation/retrieval_log.json` with the canonical URL, the host,
the claimed issuing authority and the attempt timestamp.

The block is an allowlist, not a transient failure: `pypi.org` and `github.com` answer, every
`.gov` host and `archive.org` do not. No alternative fetch path was used to route around it —
the policy is a technical restriction set by the environment owner, and the project's own
source rules forbid circumventing technical restrictions.

The bytes are also not recoverable locally. Every object in the repository's full git history
was hashed against the four expected digests: **no match, and no PDF blob has ever been
committed**. The layout cache holds only fixture documents. One document (CHP) *was* retrieved
in an earlier session — `data/audit/retrieval/CAN-S05.json` records the fetch at
2026-09-20T06:57:14Z — but its bytes lived in a git-ignored directory that did not survive the
container.

`scripts/fetch_layout_validation.py` now refuses three things it previously accepted: a
redirect onto a different host, a response whose content type is not `application/pdf`, and
any body whose SHA-256 does not match. A 200 is not provenance, and a mirror is not an
authoritative source.

### The adjudication instrument, and what it exposed

The parser must not define its own ground truth, so the adjudication set is now a first-class
artifact (`src/radiocorpus/evaluation/adjudication.py`, ADR 0008). One record per candidate,
one verdict per claim that candidate makes, and three rules: **UNADJUDICATED is never read as
agreement**, a complete fact requires every claim, and recall is computed only against a
reviewer-supplied inventory of what a document contains.

The worksheet (`data/adjudication/real_document_worksheet.jsonl`) is filled as far as the
available evidence allows, in two clearly separated passes.

**Pass 1 — restating the previous review.** Every flag the independent reviewer set becomes the
corresponding verdict. Nothing is re-judged and nothing is inferred from a question that was
never asked: the old instrument answered **6 of the 15 claims**, and the other nine were left
open.

**Pass 2 — claims the candidates never made.** A claim absent from a candidate is a fact about
the *candidate*, not about the document, so it can be decided without the source. This closed
the remaining nine — and what it closed them with is the finding:

| claim | verdict | candidates |
|---|---|---|
| `issuing_authority_correct` | MISSING | **116 / 116** |
| `procedure_actor` | MISSING | 27 / 27 |
| `communication_action` | MISSING | 27 / 27 |
| `governed_object` | MISSING | 27 / 27 |
| `communication_medium` | MISSING | 27 / 27 |
| `condition_correct` | MISSING | 27 / 27 |
| `exception_correct` | MISSING | 27 / 27 |
| `context_complete` | MISSING | 27 / 27 |

The audit's "0/27 procedures with correct applicability scope" was never a scoring problem.
**The scope was not wrong — it was absent.** A v2 procedure candidate is a sentence with a
topic label and nothing else (`applicability_scope: null`). It could not be a complete fact
because it never made most of the claims a fact requires.

That gap is now closed in the parser. `ProcedureCandidate` v4 carries a **decomposition**:
who must act, which communicative act, and what that act governs, each a span of the rule
sentence with its offsets and the rule that located it (ADR 0009). A current-parser procedure
candidate makes **13 claims a reviewer can judge** where v2 made 7 and left 6 unanswerable —
only `issuing_authority_correct` is still decided by absence, and that is a gap in the source
ledger rather than in the parser.

Measured against the plan each sentence in the randomized corpus was written from — the only
ground truth available while the real documents are unreachable — **precision 1.000 and recall
1.000 over 61 rules, 0 elements differing from their plan, all 61 fully decomposed**. Building
it also exposed a layout defect it had not caused: a revision stamp with no full stop was being
merged into the sentence below it, so a rule's subject came out as
`Revision Date: 10-11-19 … Units`. That is fixed at the layout layer, with a date guard in the
decomposition as well.

The worksheet above still shows those claims MISSING because it is seeded from the **v2**
candidates the four documents produced. The decomposition changes what a reviewer will be
asked about the *next* time those documents are parsed; it cannot retroactively change what v2
claimed.

A mechanical verdict is never mistaken for a review: every record names the claims that were
decided by absence, and the summary separates them.

| claims | count |
|---|---|
| decided by the reviewer | 579 |
| decided by absence from the candidate | 305 |
| still open | 0 |
| **decided by a human** | **0** |

Learner safety is deliberately unreachable by the mechanical pass — whether a fact is safe to
put in front of a learner is a judgement, not a shape — and a test asserts it stays open until
somebody decides it.

### Decomposition coverage on real sentences

The 1.000 precision and recall the decomposition scores on the randomized corpus says nothing
about real documents: those sentences were written by the same code that scores them, in the
shapes it was built to produce. The question that matters is **coverage** — what fraction of
the sentences an agency actually writes yields an actor, an act and an object at all.

That question can be answered now, without the blocked PDFs, because a decomposition is a
function of the sentence alone. `data/audit/real_facts.jsonl` holds the verbatim `rule_text`
the previous parser read out of the retrieved documents: **47 distinct real rule sentences**.
The committed FBI data dictionary supplies a second, out-of-domain sample.

| sample | sentences | coverage |
|---|---|---|
| randomized corpus (generated here) | 61 | **1.000** |
| **real rule sentences** | 47 | **0.191** |
| real third-party document, modal-bearing sentences | 6 | 0.000 |

| element located | rate on real sentences |
|---|---|
| actor | 0.404 |
| communication action | 0.277 |
| governed object | 0.255 |

Most of the refusals are **correct**. `no_communication_verb_after_modal` accounts for 21 of
the 38, and the sentences behind it are records rules, data-entry rules and movement orders —
"A copy will be retained in the unit files", "the code ZZ should be entered in the LIT Field",
"a Department police employee shall be immediately sent to the location". The sample is not a
clean corpus of radio rules: it is what an earlier parser emitted, and 16 of the 27 audited
candidates were judged meaning-unsupported. A refusal on a sentence that is not a radio rule
is the parser working.

The residue is honest limitation. Nine sentences put the communication verb further from the
modal than the window allows, three have a subject the leading-clause rule cannot step over
("In instances where a license plate has been issued, …"), and one carries no modal at all.
None of those constants were loosened to raise the number: every example behind them in this
sample is a non-radio sentence, and tuning a threshold against a sample that does not contain
the thing being measured would be fitting to noise.

**Two defects were found by running real sentences, and both are fixed.**

1. **A passive made its patient the actor.** "The location will be relayed the assigned unit"
   produced a *complete* decomposition with `actor = "The location"` — a confident false
   statement about whom an agency directs, which is the worst outcome this instrument can
   have. In a passive the phrase before the modal is what the act is done *to*. The actor is
   now taken only from a `by`-phrase that names a role, and is absent otherwise. This is why
   the actor rate above is 0.404 and not 0.808: **19 of those located actors were passive
   patients, and removing them is a precision gain showing up as a coverage loss.**
2. **A recipient marked by a preposition was not read.** "The assigned supervisor must
   acknowledge **to** the OEMC dispatcher **that** he or she is monitoring the pursuit" yielded
   no object. The shape is now handled, and a `that`-clause is taken whole rather than
   truncated to a noun phrase — reading it as a phrase had reported "he" as the thing
   communicated.

What this measures and what it does not: coverage, and the reasons for refusal. Not accuracy.
Whether a located actor is the *right* actor still needs a reviewer — but unlike every other
real-document question in this project, the evidence is the sentence itself, and the sentence
is present.

### Real-document metrics

Completeness is reported twice, because one number conflates two different failures. The
parser is answerable for the meaning, the normalised value, the agency and the region. It is
not answerable for who issued the document (a property of the source ledger) or for learner
safety (the downstream human gate).

| family | candidate meaning | **extraction complete** | learner-ready | recall |
|---|---|---|---|---|
| code_meaning | 0.444 (24/54) | **0.444** (24/54) | 0.000 (0/54) | null — no inventory |
| phonetic_letter | 0.765 (26/34) | **0.000** (0/34) | 0.000 (0/34) | null |
| procedure_rule | 0.407 (11/27) | **0.000** (0/27) | 0.000 (0/27) | null |

Three different stories, which a single number would have hidden:

* **Codes.** Whenever the meaning was right, everything the parser owed was right. The 0.444
  is a meaning problem, not a completeness problem.
* **Phonetics.** Meaning supported on 26 of 34, but the reviewer marked the normalised pair
  wrong on **all 34** — the letter and the word were recovered, the normalised mapping was
  not. The gap between 0.765 and 0.000 is exactly what the coarser instrument could not show.
* **Procedures.** Zero, because the candidate never decomposes the rule.

Learner-ready is 0.000 everywhere, blocked by two systemic claims rather than by individual
errors: the issuing authority is absent from all 116 candidates, and the reviewer judged
**0 of 116** learner-safe. `blocking_claims` in the artifact reports this per family, so a
systemic gap is never read as 116 separate mistakes.

Structural failures are reported per class, not aggregated: for codes, 22 adjacent-column
bleed, 7 lost wrapped continuation, 1 date/revision misread; for procedures, 9 semantic
misclassification, 4 incorrect condition/exception scope, 1 header/footer contamination.

**Every figure above is for parser v2.** The artifact states this in a `candidate_provenance`
block that refuses to let an older parser's numbers be read as the current one's. There are no
real-document metrics for the current parsers, because there are no real documents.

### Real third-party PDFs: two defects nothing synthetic had found

Every PDF this repository had ever parsed was written by this repository. `data/fixtures/real/`
now holds one that was not: the FBI NIBRS data dictionary, a US government work released under
CC0 in the Crime Data Explorer repository, pinned by commit and hash. It is not a radio-protocol
source and is never ingested as evidence about any agency; it exists to exercise the gates
against real-world PDF structure. Running it found:

1. **A letter-keyed code table read as a phonetic alphabet.** Its sex, race and offence tables
   pair a letter with a word beginning with that letter — `M = Male`, `F = Female`,
   `A = Attempted`, `C = Completed` — which is exactly the shape of a phonetic mapping. **17
   false candidates across two real documents.** A spelling alphabet fills a contiguous stretch
   of A–Z; the NIBRS tables span 6 to 23 letters and fill 0.30 to 0.50 of that range. Emission
   now requires that density, with a tighter floor for short runs. Phonetic parser → v5.
2. **A document that yielded nothing, silently.** A real PDF whose text is drawn as vector
   outlines produces no blocks, and cannot trigger the OCR gate because it carries no image.
   Returning an empty document without comment is indistinguishable from successfully parsing a
   blank one — the shape of an undetected scan. The layout now warns `no_text_extracted`.

Both fixes cost nothing measurable elsewhere: the audited replay figures, the nine fixture
scores and the 300-document stress corpus are all unchanged.

### What real-document metrics still do not exist

* No precision or recall for the **current** parsers on any of the four validation documents.
* No complete-fact precision for the **current** parsers on any real document. The figures
  above are v2's, and they are computable only because the claims v2 omitted can be decided
  from the candidate itself.
* No recall on any real document, because no inventory of what those documents contain exists.
* No human adjudication of anything. Every reviewer verdict in the corpus was recorded by an
  agent, and 305 of the 884 claim verdicts were decided by absence rather than by review.
* No verdict on any claim a candidate *did* make that the previous reviewer did not judge.
  Those need the documents, and the worksheet leaves them open by design.

## Randomized geometry

The nine fixtures above were written by the same author as the parsers, so a perfect score on
them partly measures how well they were aimed. `data/evaluation/layout_stress.json` answers a
harder question: **does the stack survive geometry it has never seen?**

300 documents are generated from seeded plans that vary column count (1–4), gutter width
(6–40 pt), font size (7–10 pt), leading, page count, repeated furniture, headings, and whether
a code table is a two-cell row or an inline series. Every code, meaning, letter and decoy is
decided *before* any parser runs, from an invented vocabulary; nothing is read back from a
candidate. Each plan is also checked for self-consistency — a page whose text falls outside
its own column is geometry no document has, and scoring detection on it would measure the
generator's arithmetic rather than the parser.

| measure | result |
|---|---|
| documents | 300 |
| columns detected exactly | 238 |
| columns conservatively merged | 62 |
| **columns invented** | **0** |
| code_meaning | precision **0.996**, recall **0.982** (tp 1779, fp 7, fn 32) |
| phonetic_letter | precision **1.000**, recall **1.000** (tp 1898) |
| revision dates emitted as codes | **0** |
| documents with no radio act yielding a procedure | **0** |
| plans whose text overflows its column | **0** |

The two directions are not equivalent and are not scored as if they were. Merging two columns
loses the facts in one table; *inventing* a column corrupts every line on the page. Zero
inventions across 300 documents is the result that matters; the 62 merges are the documented
conservative behaviour, concentrated at gutters of 6–9 pt.

### What this found

Building the corpus exposed three defects that the hand-written fixtures could not, each now
fixed and covered by a test in `tests/test_layout_stress.py`:

1. **A one-column phonetic alphabet was lost entirely.** Every `LETTER WORD` line is short and
   all-capitals, so the layout layer types it as a heading on typography alone, and the
   phonetic parser skipped every heading. The hand-written alphabet fixture happens to be
   two-column and never took this path. Headings may now carry a pair, but only under an
   explicit alphabet heading or where nearly every block in the region is itself a pair — a
   directive page whose sections start with letters cannot reach that density, so the
   enumerated-heading false positive stays closed. Recall on alphabet documents went from
   0.40 to 1.000.
2. **A wrapped meaning cell was truncated.** In a two-cell row, only the first line of a
   meaning was kept; the remainder sits on following rows whose key column is empty. That
   emptiness is now the evidence that joins them. A truncated meaning is a *wrong* fact, not a
   partial one, which is why this was treated as the severe direction.
3. **The tail of a long line was handed to the next column.** A detected column band stops
   where the typical line in that column ends, because everything beyond is blank on most
   rows; the tail of an unusually long line fell outside every band and was attached to the
   nearest edge — sometimes the neighbour's. Column membership is now decided by the column
   *starts*, which is the edge a left-aligned column actually has.

A fourth change came out of the same measurements: the minimum gutter is now the larger of a
6 pt floor and three times the page's own median word spacing. A constant in points means
something different at 7 pt than at 12 pt.

## Threshold sensitivity

`data/evaluation/threshold_sensitivity.json` sweeps the three column-detection thresholds over
120 documents — 45 combinations of minimum gutter (3–18 pt), gutter occupancy tolerance
(0.0–0.30) and minimum rows per band (2–5). A setting is **unusable** if it invents a column on
any document, whatever its exact-match rate.

| finding | evidence |
|---|---|
| The values in use sit on the top plateau of usable settings | exact 0.758, tied with every other usable setting at tolerance 0.15 |
| Occupancy tolerance is the sensitive parameter | every unusable setting has tolerance 0.30; none at 0.0 or 0.15 invents a column |
| The gutter floor is inactive below ~9 pt | the font-relative rule dominates, so 3, 6 and 9 pt give identical results |
| Minimum rows per band barely matters | 2 and 3 are identical; 5 costs ~7 points of exact match |

The chosen values are therefore not a fitted peak: they are the widest safe setting, and the
next step in the permissive direction (tolerance 0.30) is the one that starts inventing
columns. The thresholds remain tuned against synthetic geometry, which is weaker evidence than
a real corpus.

## Leave-one-document-out

Four folds, each holding out one document. The parsers contain no agency-specific or
document-specific branch, enforced by
`tests/test_layout_extraction.py::test_no_agency_specific_parser_branches`, so each fold is a
genuine held-out measurement. Per-fold figures are in `data/evaluation/lodo.json`.

## Performance

159 ms total for the nine fixtures (6–76 ms each, 1–3 pages). Real-document timing is
unmeasured. Layout is cached by content hash, so the cost is paid once per document version.

## Artifacts

| file | contents |
|---|---|
| `data/evaluation/gold_labels.jsonl` | 116 derived correction labels with original flags |
| `data/evaluation/replay_outcomes.jsonl` | per-candidate result in both replay modes |
| `data/evaluation/metrics_replay.json` | the tables above, per family and per document |
| `data/evaluation/lodo.json` | leave-one-document-out folds |
| `data/evaluation/fixture_truth.json` | exhaustive fixture ground truth |
| `data/evaluation/fixture_eval.json` | fixture precision and recall |
| `data/evaluation/fixture_candidates.jsonl` | every fixture candidate, for inspection |
| `data/evaluation/real_document_metrics.json` | all four documents recorded MISSING with the block reason |
| `data/evaluation/layout_stress.json` | 300 randomized documents, per-document results and summary |
| `data/evaluation/threshold_sensitivity.json` | column detection under 45 threshold combinations |
| `data/adjudication/real_document_worksheet.jsonl` | one record per candidate, one verdict per claim |
| `data/adjudication/worksheet_coverage.json` | which claims the previous review actually judged |
| `data/evaluation/real_document_adjudicated_metrics.json` | real-document metrics, with every unadjudicated figure null |
| `data/evaluation/real_pdf_probe.json` | layout behaviour on real third-party PDFs |
| `data/evaluation/decomposition_coverage.json` | decomposition coverage on real sentences, with refusal reasons |
| `data/evaluation/ocr_validation_status.json` | what OCR validation established, and what it did not |
| `data/fixtures/real/MANIFEST.json` | identity, issuer, licence and origin commit of the real fixtures |
| `data/raw/layout-validation/retrieval_log.json` | per-document acquisition attempt, host and claimed issuer |
| `data/raw/layout-validation/MANIFEST.json` | document identity, expected hashes and page counts |
