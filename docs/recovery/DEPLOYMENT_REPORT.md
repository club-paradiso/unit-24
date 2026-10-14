# Verified recovery release — 2026-10-14 UTC

## Functional release record

- PR: https://github.com/club-paradiso/unit-24/pull/10 (merged after all four exact-head gates passed).
- Verified recovery head: `a749d80441c253eb65805f5493e875c38eb486c8`.
- Functional production merge: `6446fcc4ce74f04521b893b38ab44bf79925a687`.
- Exact-head CI: https://github.com/club-paradiso/unit-24/actions/runs/38494501402 — checks, web, firestore-rules and preview all successful.
- Approved Preview: https://unit-24-3nl3aphl1-club-paradiso.vercel.app (`dpl_BdyeQzJdt61eYk63JWZjdcVny3L4`).
- Functional production: https://unit-24-dvqy50p44-club-paradiso.vercel.app (`dpl_9VeBm1p9E4rbT9Qr8jKm9jqLBFME`, READY, target production, source git, exact merge SHA above).
- Primary domain: https://unit-24.vercel.app; production HTML loads `/assets/index-C18Ho0a_.js` and `/assets/index-DAu8E1e7.css`.
- Production smoke: https://github.com/club-paradiso/unit-24/actions/runs/38495765818 — **238 passed**, 14 explicit loopback-worker-fixture skips, all seven projects tested.
- Main CI: https://github.com/club-paradiso/unit-24/actions/runs/38495723876 — Python/web/rules successful; PR-only Preview job intentionally skipped on push.
- Legacy domain https://unit-24-3o8p.vercel.app returned HTTP 307 to the primary domain; aliasError null.

This is the independently verified functional release record. A later documentation-only publication may create a new deployment with the same web tree/assets; its metadata does not replace the functional evidence above.

## Actual platform configuration

Vercel team Club Paradiso (`team_YA4bUgBlPWrfBJGi6nea1W8W`), project unit-24 (`prj_sHUYdgZBCPGw4FiRhlOKGFGIG2kr`), framework Vite, Node 24. Environment metadata was rechecked immediately before release: no project variables returned, hidden production variable count 0. No values were decrypted. Firebase therefore remains unconfigured in the shipped application.

Baseline build events executed the exact web/vercel.json ignore/install/build commands, produced matching web assets and served its CSP. This establishes the effective web configuration. The connector does not expose rootDirectory; that dashboard field is not claimed as independently read. Root vercel.json remains unchanged.

Preview's optional Vercel feedback injection violated the existing CSP on every route. Project enablePreviewFeedback was set false and fresh Preview HTML verified without that script. CSP and access protections were not weakened. Existing immutable Previews retained their old injection and were not released.

A forced same-commit redeployment (`dpl_HbuqZznS7MMRwpi2fKg3SUrN38QS`) was canceled by the old source-only ignore command. The active web ignoreCommand and project ignored-build override were removed. Every head now receives a concrete Preview, including deployment-setting/documentation changes. CI resolves a successful non-production deployment for the exact PR head and tests its immutable URL.

Main protection remains unenforced at the final inspection (protected=false, required check contexts empty). This session explicitly checked all gates and used expected-head merging; future owners should require checks/web/firestore-rules/preview with up-to-date branches and forbid force pushes/deletion. No callable branch-protection mutation was available through this GitHub connector.

## Observed update and learner behavior

An actual production Cloud Chrome client loaded the baseline `/assets/index-4BslfJ1e.js` plus `/registerSW.js`, saved 10-14 → Provide escort at 1/10, and remained open across release. Its first ordinary reload still loaded the legacy shell while registering the recovery worker. Its second ordinary reload loaded `/assets/index-C18Ho0a_.js`; the exact question, selected answer and feedback remained 1/10. No site data was cleared and no forced page reload was used.

The same real production client then visited all nine first-lesson cards. Card 2, first assessment feedback and final 5/5 completion each survived explicit reload. See evidence/production-observation.json and the three production screenshots. These are test learner interactions, not human source adjudication or physical-phone evidence. Cloud-browser metadata-extension errors were observed with chrome-extension source URLs; application console/CSP assertions passed in deployed smoke.

## Rollback

Retain this recovered deployment/SHA as the rollback point for future releases. Emergency baseline: `0253df8d3397caa184f8d89c851eb40537b98b0e`, `dpl_7TvFyiZXC7LQ1yodMp3ZRxcvo2pf`, https://unit-24-hkxrixkru-club-paradiso.vercel.app. That baseline has the known lesson-reload defect.

Revert a defective future change through a verified PR or restore the recovered deployment in Vercel. Progress stays schema v1 with additive fields; no destructive migration was performed. Export progress before an emergency downgrade: old code ignores new lesson drafts. Never clear localStorage or delete cloud progress to solve an asset/cache update problem.
