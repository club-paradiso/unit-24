# Human review decisions (CHP 254 card)

This directory is the **only** place a human decision about the CHP learning content enters the
repository. `radiocorpus export-learning` reads it; CI fails if any line is invalid.

Decisions are made by a person comparing entries with the card itself. Use the review page of
the learner app (`/review`): it lists all 85 extracted entries and downloads your decisions in
this format. Append the downloaded lines to `chp_reviews.jsonl` in a pull request.

## `chp_reviews.jsonl` — one decision per line (schema `human-review-1`)

| Field | Meaning |
|---|---|
| `schema` | `"human-review-1"` |
| `fact_id` | the entry, as listed on the review page |
| `document_sha256` | SHA-256 of the card you reviewed; must be `eec212ac94b0f12cbfbf5286cde85995e96e83d66f40939aa9c3d3406c1e6064` |
| `decision` | `ACCEPT` (the shown answer matches the card; taught entries only), `REJECT` (should not be taught; `notes` required) or `CORRECT` (type the meaning as printed) |
| `meaning_as_printed` | for `CORRECT` only, otherwise `null`. If the text is not in the recorded excerpt, `notes` must say where you read it |
| `page` | page of the card (1 or 2) |
| `reviewer` | your name or handle |
| `reviewed_at` | `YYYY-MM-DD` |
| `notes` | free text, `""` for none |

Rules applied by `src/radiocorpus/learning/human_review.py`:

* The file is append-only. A later line from the same reviewer for the same entry replaces
  that reviewer's earlier one.
* Different reviewers must agree. If they do not, the entry is shown as disputed and is not
  human-verified.
* A corrected entry that no lesson lists is taught in an automatic "Newly reviewed entries"
  lesson; a rejected entry is dropped from its lesson.
* Human verification is reported in the learner app. It does not change the research corpus's
  eligibility policy, which stays `RESEARCH_ONLY` until that pipeline models human acceptance.

## `chp_source_review.json` — optional, about the card itself (schema `human-source-review-1`)

```json
{"schema": "human-source-review-1",
 "document_sha256": "eec212ac…6064",
 "printed_revision": "text printed on the card, or null",
 "listed_at_url": "https://www.chp.ca.gov/… page listing the card, or null",
 "listed_checked_at": "YYYY-MM-DD or null (with listed_at_url)",
 "reviewer": "name", "reviewed_at": "YYYY-MM-DD", "notes": ""}
```

A listing shows the card was published on that date; the app says so and does not call it
proof of current operational use.
