# Deployment report

Baseline and current known production commit: `0253df8d3397caa184f8d89c851eb40537b98b0e`.

- Production: https://unit-24.vercel.app
- Immutable baseline: https://unit-24-hkxrixkru-club-paradiso.vercel.app
- Deployment: `dpl_7TvFyiZXC7LQ1yodMp3ZRxcvo2pf` (READY)
- Vercel team: Club Paradiso (`team_YA4bUgBlPWrfBJGi6nea1W8W`)
- Project: `unit-24` (`prj_sHUYdgZBCPGw4FiRhlOKGFGIG2kr`)
- Framework: Vite; runtime setting Node 24.
- Environment metadata: no project variables returned, hidden production variable count 0. No secret values were requested.
- Build events match web/vercel.json's ignore/build commands and prior generated asset names. The connector project response did not expose rootDirectory. Both vercel.json files are preserved.
- Previous baseline CI: https://github.com/club-paradiso/unit-24/actions/runs/38335741287
- Previous baseline production smoke: https://github.com/club-paradiso/unit-24/actions/runs/38335776587

Recovery release is pending. Do not merge until current branch CI, immutable Preview user journeys, update/offline checks and source-label checks pass. Production then requires independent smoke and commit/domain verification. No baseline production setting or user data has been changed.

Rollback: retain baseline deployment and SHA. Revert the recovery commit or restore the baseline deployment through Vercel if needed. Progress schema remains v1 with additive fields; no destructive migration. Export learner progress before any manual troubleshooting; never clear site storage as an update fix.

## Recovery configuration reconciliation

The effective web configuration was confirmed by baseline build events executing its exact ignore command, npm commands and output asset identity, plus its CSP on live HTTP responses. Root vercel.json remains unchanged. The project API does not expose rootDirectory, so that dashboard field is not claimed as independently read.

Preview verification found Vercel's injected feedback script blocked by the declared CSP. Project `enablePreviewFeedback` was set false; CSP was not broadened and access protections were not changed. Existing deployment HTML retained its immutable injection setting, so a fresh Preview is required.

A forced same-commit rebuild was canceled by the old ignored-build command (`dpl_HbuqZznS7MMRwpi2fKg3SUrN38QS`). Exact-head Preview gates and deployment-setting changes cannot rely on a source-only skip rule. The active web ignoreCommand was removed and the project ignored-build setting cleared. Every recovery/documentation commit now gets a concrete deployment and the same verification gates. This enables builds; it does not disable CI or security checks.
