# Independent audit handoff — layout-aware extraction

**Branch:** `opus/layout-aware-extraction` · **Base:** `7d8e838` (main)
**Parser versions:** layout-2, code v4, phonetic v4, procedure v3
**Parser-specific status:** EXTRACTION_NOT_READY · **Project status:** NOT_READY (unchanged)

## What to audit, and what is already conceded

This sprint changed only the transformation `document → candidates`. No evidence, currency,
source-independence, eligibility, identity or conflict rule was touched. If you find one
weakened, that is a defect, not an intended trade.

Three claims are **not** made and should not be looked for:

1. No precision figure on the real documents. None was parsed; all four hosts were refused by
   the egress policy. `data/evaluation/real_document_metrics.json` records each as MISSING
   with its block reason.
2. No complete-fact precision. The review's labels attach to the previous parser's candidates;
   the new candidates differ in text and carry new scope fields, so the labels do not transfer.
3. No recall on real documents. Recall is reported only for the synthetic fixtures, whose
   ground truth is exhaustive by construction.

## The three questions that matter most

**1. Is the gold derivation faithful?** `src/radiocorpus/evaluation/gold.py` maps the
reviewer's own flags onto a taxonomy. It adds no judgement about any document. Every record
keeps `original_flags`, `derivation_rule` and `reviewer`. `data/audit/fact_audit.jsonl` is
byte-identical to main — a test asserts it. If the derivation misrepresents the review, every
metric downstream is wrong.

**2. Are the new gates principled or fitted?** The rejections are shape-based, not literal:
date detection is a token-boundary rule (`numeric_token_is_date`), not a match on `09-11-18`;
heading rejection is an enumerator rule, not a match on `C. COMMUNICATIONS`. A test asserts no
parser source contains an agency or document token. Judge whether the rules would survive a
fifth document.

**3. Is the procedure gate too aggressive?** It is the largest behaviour change: 27 candidates
became 10. Bare `copy` was removed from the acknowledgement trigger because all three
candidates it produced in the audited set were document copies and no supported candidate
depended on it. That is an evidence-based removal on a sample of three. Challenge it.

## Reproducing

```bash
uv sync
uv run pytest                                        # 155 passed
uv run ruff check src tests scripts
uv run radiocorpus check-invariants                  # run after rebuilding the corpus
uv run python scripts/make_layout_fixtures.py        # regenerate the nine fixtures
uv run python scripts/evaluate_extraction.py         # regenerate every evaluation artifact
uv run python scripts/stress_layout.py               # regenerate the randomized corpus and sweep
rm -f data/intermediate/corpus.sqlite* && uv run radiocorpus run-canary --skip-acquire
```

`check-invariants` reads a git-ignored local database. A database left from an earlier branch
will report violations that belong to that database, not to this branch; main shows 84 such
violations from the same stale file. Rebuild before judging.

## Completing the blocked work

```bash
uv run python scripts/fetch_layout_validation.py     # verifies SHA-256, refuses mismatches
uv run python scripts/run_layout_validation.py       # parses and writes real-document metrics
```

Then adjudicate `data/evaluation/real_document_candidates.jsonl` against the sources. Expect
to re-label rather than reuse: the candidates are differently shaped.

## Artifact index

| file | what it is |
|---|---|
| `data/evaluation/gold_labels.jsonl` | 116 derived labels, original flags retained |
| `data/evaluation/replay_outcomes.jsonl` | per-candidate outcome, both replay modes |
| `data/evaluation/metrics_replay.json` | per family, per document, failure-class elimination |
| `data/evaluation/lodo.json` | leave-one-document-out folds |
| `data/evaluation/layout_stress.json` | 300 randomized documents, ground truth from the generation plan |
| `data/evaluation/threshold_sensitivity.json` | column detection under 45 threshold combinations |
| `data/evaluation/fixture_truth.json` / `fixture_eval.json` / `fixture_candidates.jsonl` | fixture ground truth, scores, candidates |
| `data/evaluation/real_document_metrics.json` | the blocked state, per document |
| `data/raw/layout-validation/MANIFEST.json` | identity and expected hashes of the four documents |
| `docs/extraction-metrics.md` | the numbers and the readiness argument |
| `docs/layout-extraction.md` | architecture and the failure each rule addresses |
| `docs/decisions/0006-pdfplumber-layout-backend.md` | backend choice and why licence decided it |

## Known weaknesses

Three entries below were unmeasured assertions in the first version of this handoff. They are
now measured, and the measurement found three defects, which are fixed. The remaining entries
are unchanged and are the ones to attack.

**Still open — attack these first**

* **Procedure scope is unadjudicated.** 0/27 audited procedures had correct scope. The new
  fields target that and nobody has checked them. This needs the real documents and a human;
  it is the single largest gap.
* **One unresolved false positive** remains in isolated replay (`CONTEXT_OMITTED`, Chicago
  location rule). It is flagged `context_complete=False`; with the real page its following
  exception would be captured, which is untested.
* **Seven true code facts are lost** in page-group mode. They need geometry; whether the real
  page supplies it is unverified.
* **No OCR validation against a real scan.** The gate is now exercised against a synthetic
  image-only page (refuses, emits nothing, refuses again on blank OCR output), but no real
  scanned document has been through it.
* **Column merging at narrow gutters.** 62 of 300 randomized documents had columns merged
  rather than split, concentrated at gutters of 6–9 pt; in 3 of them the merge let one
  column's words reach a neighbouring meaning. No document had a column invented.
* **`data/evaluation` is committed.** It is generated output; it is committed so the audit can
  read it without a network, and it is regenerable by the commands above.

**Measured since, with what it found**

* ~~Fixtures are self-designed.~~ `data/evaluation/layout_stress.json` adds 300 documents
  generated from seeded plans that are their own ground truth, with an invented vocabulary and
  geometry the parsers have never seen. Result: 0 invented columns, code precision 0.996 /
  recall 0.982, phonetic precision and recall 1.000, 0 revision dates emitted as codes, 0
  procedures from documents containing no radio act. It found a one-column alphabet being lost
  entirely, a wrapped meaning cell being truncated, and a long line's tail being handed to the
  next column. All three are fixed and covered by tests.
* ~~Column detection thresholds are tuned on one adversarial layout.~~
  `data/evaluation/threshold_sensitivity.json` sweeps 45 combinations. The values in use are on
  the top plateau of settings that never invent a column; the occupancy tolerance is the
  sensitive one, and the next permissive step (0.30) is where inventions begin. The gutter
  floor is now font-relative, so the constant matters only below ~9 pt.

Both remain synthetic evidence. Neither changes the readiness status.
