# Content integrity — recovery

No evidence labels, human records, source hashes or excluded candidates were promoted during recovery.

| Measure | Count/status |
|---|---|
| Reviewed candidates (existing AI adjudication) | 85 |
| Teachable research-only items | 50 |
| CHP radio codes | 24 |
| CHP card alphabet | 26 |
| Excluded candidates | 35 |
| Human-verified items | 0 |
| Operational-currentness-verified items | 0 |
| Operationally learner-safe items | 0 |
| Source quality | Unverified |

Source: https://www.chp.ca.gov/globalassets/chp-254---aural-brevity-card---01-2021-v2.pdf
Stored identity: SHA-256 `eec212ac94b0f12cbfbf5286cde85995e96e83d66f40939aa9c3d3406c1e6064`, 60,110 bytes, 2 pages. The filename is not proof of publication, effective date or operational currentness. Remote PDF text was accessible during investigation; the subsequent byte and geometry reconciliation is recorded below.

The 50 learner items remain RESEARCH_ONLY. Official hosting does not certify currentness. Alphabet words are CHP card words, not a universal alphabet. The 35 excluded entries remain excluded until source-backed adjudication; no count expansion was attempted.

`data/adjudication/human/chp_reviews.jsonl` remains empty. Review UI exports are proposals for repository ingestion, not automatic publication. A human must compare original PDF pages, record reviewer identity/date/source hash, validate JSONL and regenerate content using the documented human-review workflow. AI-authored decisions must never be inserted as human decisions.

Historical extraction measurements are not new current-parser estimates. Miami/South Miami entity quarantine, search-only websites, Chicago exclusion/hash mismatch, document hash locks and eligibility gates remain intact. Seven previously lost code facts, incomplete procedure decomposition, narrow gutters, raster-scan OCR, context false positives and parser-derived gold labels remain research limitations. No independent human-labelled document holdout was created in this recovery. Synthetic tests do not replace it.

## Fresh original-document observation

The canonical PDF was retrieved on 2026-10-13 UTC: 60,110 bytes; SHA-256 exactly matches the stored identity above; rendered 2 pages. Its visible page-1 header reads **CHP 254 (REV 10-21) OPI 048**. This differs from the filename-derived `01-2021 v2` display. The printed revision is an AI observation, not a human source review, publication/effective date, or evidence of current use. Existing human-gated metadata has not been promoted.

`evidence/chp-ai-reconciliation.json` records all 85 candidates against the rendered original: 50 retained items match after the documented punctuation/blank normalization; 29 rejected code candidates have source-backed corrected readings but remain excluded; 6 rejected alphabet/system candidates remain unsupported as alphabet entries. The suffix column must not be confused with the separate phonetic alphabet. None was inserted into human review records or automatically restored to lessons.

`evidence/current-parser/real_document_metrics.json` is a fresh current-parser run on this exact PDF, with its code fingerprint: 55 code candidates, 31 phonetic candidates, 0 procedure candidates. It still includes suffix words in phonetic candidates, while classifying the combined alphabet LOCAL rather than falsely certifying APCO. These are yields, not precision/recall estimates. The other three documents were absent in this run and explicitly report MISSING. Historical evaluation files were not overwritten.

Reproduce without overwriting historical metrics: place the hash-verified PDF at the manifest filename, run `uv run python scripts/run_layout_validation.py --output-dir docs/recovery/evidence/current-parser`. It returns 1 while any other manifest PDF is absent. See the committed output for exact parser versions and fingerprint.

## Released integrity check

At functional release 6446fcc4ce74f04521b893b38ab44bf79925a687, export-learning regenerated chp.json byte-for-byte without a diff; human/chp_reviews.jsonl still has 0 lines. Counts remain 85 AI-reviewed candidates, 50 research-only learner items (24 codes/26 letters), 35 excluded, 0 human verified, 0 operational-currentness verified. Canonical-question guards now prevent structurally valid backups from injecting unsupported subjects, answers, distractors or source references. They do not turn application progress into source verification.
