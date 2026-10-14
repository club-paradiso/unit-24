# Remaining blockers

## Technical work not completed

- Complete expanded browser regression run, fix failures, verify immutable Preview and production before merge/release.
- Test actual old-service-worker to new-service-worker upgrade and offline reconnection; current prompt is not yet browser-verified.
- True simultaneous localStorage writes and additive same-item sync counts are not solved by read-before-write/LWW. Accounts must not be marketed as lossless multi-device learning.
- Account switching isolation, redirect sign-in completion, deletion versus pending pushes and real network retries still need adversarial integration verification.
- Flashcard deck cursor does not persist, though each grade does.
- Current-parser measurements were reproduced for CHP only, and all 85 existing candidates received an explicitly AI-only original-PDF reconciliation. Independent precision/recall, other documents and human-labelled complete-fact inventories remain incomplete. Historical metrics are unchanged.
- Main branch protection was not enforced at inspection; passing checks must be explicitly verified before merge.

## External configuration

No deployed Firebase configuration exists in returned Vercel environment metadata. Configure an actual authorized Firebase project, Auth providers/domains, Firestore, reviewed production rules and environment-separated public VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, VITE_FIREBASE_PROJECT_ID, VITE_FIREBASE_APP_ID. Test real sign-in, refresh, mobile redirect, account switching, reconnect, two-device merge, invalid remote state and deletion before enabling the feature. Client config is not a credential and rules remain the authorization boundary. Do not invent values or claim rules were published.

## Human source verification

Zero human decisions. Original pages need identified human reviewers with source hash/date evidence. Operational currentness remains unknown. Use existing review/export/validation/regeneration workflow; an AI assessment cannot fill this gap. Excluded candidates must remain excluded pending substantiation.

## Physical-device verification

Real iOS Safari and home-screen installation, actual Android installation, storage eviction and long-duration persistence remain unverified. Playwright WebKit/iPhone viewport must be labelled emulation.

Until release gates complete, the recovery is not complete and production retains its known lesson-reload defect.
