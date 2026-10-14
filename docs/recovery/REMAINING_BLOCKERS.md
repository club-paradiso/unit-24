# Remaining blockers — after verified core recovery

Verdict: **FUNCTIONAL_WITH_LIMITATIONS**. Core local-device research learning works in the verified browser matrix and released production. This is not an operational radio reference, a human-verified corpus, a certified physical-iOS app, or a completed account service.

## Technical work not completed

- True simultaneous localStorage writes are not transactional. Sequential edits to distinct progress records were verified; simultaneous or stale edits to the same lesson/session still need conflict handling.
- Multi-device merge is last-write-wins per item and max per-day count, not an additive event log. Same-item simultaneous work can be undercounted. Account switching isolation, redirect completion, deletion versus pending pushes and real retry/idempotency behavior need repair/integration verification before accounts are enabled.
- Flashcard grades persist; the exact deck cursor does not. Finish a deck before updating. Lesson and practice drafts/feedback are resumable.
- Current parser still admits suffix words as phonetic candidates. Seven historical lost code facts, incomplete procedure decomposition, narrow-gutter behavior, real raster-scan OCR, context false positives and parser-derived gold labels remain research gaps. Only CHP current-parser yields were rerun; other three validation PDFs were missing in that run. No independent human-labelled complete-fact holdout or new precision/recall estimate exists.
- Main required checks are not enforced by repository settings. This recovery explicitly checked every gate and merged with an expected head. Future automatic production safety requires branch protection; do not treat this procedural check as persistent enforcement.

## External configuration / controls

Vercel environment metadata remains empty. Actual Firebase project existence, providers, domains, Firestore and published rules were not established through an available management connection. Do not infer that no Firebase project exists anywhere.

Before enabling accounts: use an authorized test Firebase project for Preview; configure Google/email-link providers and exact authorized domains; provision Firestore; validate and publish reviewed restrictive rules; supply public VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID and VITE_FIREBASE_APP_ID; rebuild. Never put Admin/service-account credentials in VITE variables. First complete the technical account gaps above, then test real callback, refresh, account switching, network interruption, two-device conflicts, invalid remote data and deletion. Passing 8 emulator rules tests is not production readiness.

Owner GitHub control: protect main with up-to-date required checks **checks**, **web**, **firestore-rules**, **preview**, apply to administrators as appropriate, and disallow force pushes/deletion. Final inspection returned protected=false and no required contexts. The connector had no callable protection-write operation; no protection change is claimed.

## Human source verification

Zero human source decisions; currentness unknown; source quality UNVERIFIED; operationally learner-safe count 0. The 85-candidate reconciliation is explicitly AI-only. Do not insert it into human records or upgrade labels.

Reviewer-ready workflow:

1. Download the canonical CHP PDF and require SHA-256 eec212ac94b0f12cbfbf5286cde85995e96e83d66f40939aa9c3d3406c1e6064, 60,110 bytes, 2 pages.
2. Open /review, supply actual reviewer identity, compare original page geometry and qualifiers, record real dates and source hash. Inspect the AI reconciliation only as a proposal; independently decide.
3. Export JSONL. Submit named human decisions to data/adjudication/human/chp_reviews.jsonl through a PR using that directory's README format. Do not manufacture human=true records.
4. Run uv run radiocorpus check-invariants, uv run radiocorpus export-learning and the full CI/Preview flow. Verify deployed provenance/counts. Conflicting reviewers keep disputed entries unverified.
5. Obtain separate official current-listing/effective-date evidence before operational-currentness claims. Filename or printed revision alone is insufficient. All 35 exclusions stay excluded pending appropriate adjudication.

## Physical-device verification

Real iOS Safari/home-screen installation, actual Android installation, storage eviction, long-duration persistence, slow mobile networks and a human screen-reader journey remain unverified. Playwright WebKit/iPhone-sized results are emulation. No physical-device success was fabricated.
