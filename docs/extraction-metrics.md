# Extraction metrics and parser readiness

**Parser versions:** layout-2 (`layout_code_fingerprint` pins the source), code parser v4,
phonetic parser v4, procedure parser v3. **Baseline:** commit `7d8e838`, parser v2.

The code and phonetic parsers moved to v4 when the randomized corpus below exposed three
defects in v3. Facts already extracted keep the version that produced them; provenance records
what happened, it is not rewritten.

## Readiness status

> **EXTRACTION_NOT_READY**

This is not a statement that the parser got worse. The measured improvements below are real
and reproducible. The status is NOT_READY because the evidence needed to clear the sprint's
own quality gate could not be obtained:

1. **No real document was parsed.** All four validation documents were refused by the
   organisation egress policy (HTTP 403 at CONNECT). Nothing was substituted. Precision on
   real documents is therefore unmeasured, and the ≥95% / ≥90% targets cannot be adjudicated.
2. **Complete-fact precision is unestablished.** The independent review found 24/116 complete
   facts and **0/27 complete procedure facts** — every audited procedure had incorrect
   applicability scope. The new parser attaches scope, condition and exception fields to
   address exactly that, but those fields are unadjudicated: the existing labels were assigned
   to differently-shaped candidates and do not transfer.
3. **No OCR validation against a real scan.** The fail-closed gate is now exercised against a
   synthetic image-only page — it refuses, emits nothing, and refuses again when a supplied
   OCR backend returns blank — but no real scanned document has been through it. Synthetic
   coverage is not the same evidence, so this remains a NOT_READY item.

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
| `data/raw/layout-validation/MANIFEST.json` | document identity, expected hashes and page counts |
