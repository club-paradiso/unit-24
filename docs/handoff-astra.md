# Independent audit handoff — layout-aware extraction

**Branch:** `opus/layout-aware-extraction` · **Base:** `7d8e838` (main)
**Parser versions:** layout-2, code v3, phonetic v3, procedure v3
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
| `data/evaluation/fixture_truth.json` / `fixture_eval.json` / `fixture_candidates.jsonl` | fixture ground truth, scores, candidates |
| `data/evaluation/real_document_metrics.json` | the blocked state, per document |
| `data/raw/layout-validation/MANIFEST.json` | identity and expected hashes of the four documents |
| `docs/extraction-metrics.md` | the numbers and the readiness argument |
| `docs/layout-extraction.md` | architecture and the failure each rule addresses |
| `docs/decisions/0006-pdfplumber-layout-backend.md` | backend choice and why licence decided it |

## Known weaknesses

* **Fixtures are self-designed.** A perfect score on nine fixtures written by the same author
  who wrote the parsers is weak external evidence.
* **One unresolved false positive** remains in isolated replay (`CONTEXT_OMITTED`, Chicago
  location rule). It is flagged `context_complete=False`; with the real page its following
  exception would be captured, which is untested.
* **Seven true code facts are lost** in page-group mode. They need geometry; whether the real
  page supplies it is unverified.
* **Procedure scope is unadjudicated.** 0/27 audited procedures had correct scope. The new
  fields target that and nobody has checked them.
* **Column detection thresholds** (12 pt gutter, 85% row agreement, 3 rows) are tuned on one
  adversarial layout.
* **No OCR validation.** The gate is unchanged and untested against a scanned source.
* **`data/evaluation` is committed.** It is generated output; it is committed so the audit can
  read it without a network, and it is regenerable by the command above.
