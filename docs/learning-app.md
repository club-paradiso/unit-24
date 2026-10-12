# Learning app (`web/`)

Unit-24's learner-facing application. It teaches the radio codes and spelling alphabet on the
California Highway Patrol **CHP 254 Aural Brevity Card**, and shows the source and verification
status of every entry. Architecture decision: [ADR 0010](decisions/0010-static-learning-app.md).

## What a learner can do

| Journey | Where |
|---|---|
| Choose a jurisdiction (CHP is the only one with reviewed content) | `/` |
| See how far the content has been checked, open lessons | `/chp` |
| Study a lesson card by card, then pass a 5-question check (4/5 needed) | `/chp/lessons/:id` |
| Flashcards with self-grading ("Again" / "I knew it") | `/chp/flashcards` |
| Practice sessions of 10: mixed, codes, card alphabet, due items, mistakes | `/chp/practice` |
| Immediate feedback with the correct answer and a link to its source | during practice |
| Session summary: accuracy, missed items, newly mastered, "practise these again" | end of a session |
| Resume an unfinished session at the same question after leaving or reloading | `/`, `/chp/practice` |
| Search the reference; see the 35 entries that are not taught and why | `/chp/reference` |
| Inspect an entry: excerpt, page, document hash, review record, limitations | `/chp/items/:id` |
| Progress: accuracy, mastered, due, needs review, lessons, history, export/import/reset | `/progress` |
| Methodology and status definitions | `/about` |

## Content rules

`radiocorpus export-learning` builds `web/src/content/chp.json` from:

* `data/evaluation/gold_labels.jsonl` and `data/audit/fact_audit.jsonl` — the independent source
  review of the 85 entries extracted from the card;
* `data/audit/real_sources.jsonl` and `data/raw/layout-validation/MANIFEST.json` — source identity
  (URL, SHA-256, size, pages, retrieval time);
* `data/audit/real_conflicts.jsonl` — the five letters with a competing extraction;
* `data/learning/chp_lessons.json` — editorial lesson groupings (a teaching choice, not a claim).

An entry is **teachable** only when the review found it on the card exactly:

* **Codes** (24): gold label `TRUE_FACT` — meaning, normalisation and scope all correct.
* **Letters** (26): gold label `WRONG_NORMALIZATION` with the meaning supported. The only error
  was the extractor's claim that the alphabet is APCO 1941; the card prints *Yellow* for Y. The
  app calls it the card alphabet and claims no wider standard.

Everything else (35 entries: column bleed, lost continuation lines, suffix words read as
phonetics) is listed as *not yet teachable*, with the review's reason and **without** the
extracted meaning. Meanings are never repaired from neighbouring text, no usage examples are
written (the card gives none), and nothing is borrowed from other agencies or from NATO/APCO
alphabets.

### Status shown to learners

| Label | Meaning | Source field |
|---|---|---|
| Source-matched | An automated (AI agent) review found the entry on the card as shown. | `review.*`, `status.source_matched` |
| Not human-verified | No human has accepted it. The corpus keeps it `RESEARCH_ONLY`. | `status.human_verified`, `status.eligibility` |
| Current use unknown | The card has no confirmed revision or effective date. | `status.currentness` |

Regenerate after any change to the inputs:

```bash
uv run radiocorpus export-learning
uv run radiocorpus check-invariants   # fails if the bundle is stale
```

## Learning model

* **Spaced repetition** (`web/src/lib/srs.ts`): Leitner boxes 1–5, next review after 0, 1, 3,
  7 and 16 days. A wrong answer returns an item to box 1. A correct answer promotes it only if it
  was due, so *Mastered* (box 5) takes at least four correct recalls spread over about 11 days.
* **Exercises** (`web/src/lib/quiz.ts`): four-option questions whose distractors are other
  teachable answers of the same kind; spelling questions graded letter by letter.
* **Persistence** (`web/src/lib/progress.ts`): `localStorage` key `unit24.progress`, schema
  version 1, validated on load. Unreadable data is backed up to `unit24.progress.corrupt-backup`
  and replaced; unavailable or full storage falls back to memory with a visible notice.

## Develop, test, build

```bash
cd web
npm ci
npm run dev          # http://localhost:5173
npm run typecheck
npm test             # Vitest unit and component tests
npm run build        # type-checks, then writes dist/
npx playwright test  # end-to-end journeys + axe accessibility scans, desktop and mobile
```

Playwright uses Chromium; in CI it is installed with `npx playwright install --with-deps chromium`.

## Deploying

`npm run build` produces a static site in `web/dist/`. Any static host works, provided unknown
paths fall back to `index.html` (client-side routing). `web/vercel.json` declares this for
Vercel. Deployment is **not enabled**: the repository-level `vercel.json` keeps Git deployments
off (ADR 0007). Enabling it means pointing a Vercel project's root directory at `web/` and
turning deployments on, which is an owner decision.

## Known limitations

* No entry is human-verified, and the card's currentness is unknown. The app says so on every
  entry, but it should not be presented as an authoritative reference until a human adjudicates
  the 50 entries and the card's revision status is confirmed.
* 35 card entries, the card's "Code" status list and its statute column are not taught: the
  layout-aware candidates in `data/evaluation/real_document_candidates.jsonl` have not been
  adjudicated.
* Progress is per browser; there are no accounts or sync.
* Verified in automated Chromium only (desktop 1280×800 and Pixel 7 emulation). Not yet tested
  on physical devices, Safari or Firefox, or with a screen reader by a person.
