# Extraction metrics and parser readiness

**Parser versions:** layout-2 (`layout_code_fingerprint` pins the source), code parser v3,
phonetic parser v3, procedure parser v3. **Baseline:** commit `7d8e838`, parser v2.

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
3. **No OCR validation.** No scanned source was tested. The fail-closed gate is unchanged and
   remains a separate NOT_READY item.

Project status remains **NOT_READY** for nationwide discovery regardless of this sprint.

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
| `data/raw/layout-validation/MANIFEST.json` | document identity, expected hashes and page counts |
