# ADR 0011 — the learner app is hosted on Vercel, built from `web/` only

**Status:** accepted (2026-10-12). Revisits [ADR 0007](0007-no-vercel-deployment.md) as that ADR anticipated.

## Context

ADR 0007 turned off Git deployments because the only thing Vercel could find was the Python
research CLI, and it said the decision would be revisited "by adding the surface, not by aiming
Vercel at the CLI". ADR 0010 added that surface: a static app in `web/`, merged in
club-paradiso/unit-24#7 with unit, end-to-end and accessibility tests green. The project owner
has asked for a live website on Vercel.

## Decision

* The Vercel project `unit-24` in the Club Paradiso team, live at
  https://unit-24.vercel.app, is connected to this repository with **root directory
  `web/`** and the Vite framework preset. Vercel only reads `web/` and
  `web/vercel.json`; nothing outside `web/` is built or served, so the Python pipeline and its
  CLI stay off the network.
* The repository-level `vercel.json` (`git.deploymentEnabled: false`) is kept. It no longer
  affects the `web/` project, but it still stops any project rooted at the repository root from
  building the CLI, which is what ADR 0007 guards against.
* `main` deploys to production; other branches get preview deployments. `ignoreCommand` skips a
  build only when nothing under `web/` changed since the branch's last successful deployment
  (`VERCEL_GIT_PREVIOUS_SHA`); with no previous deployment it always builds.
* Production is public. Preview deployments stay behind Vercel Authentication
  (deployment protection scope: previews only).
* `web/vercel.json` sends a strict Content-Security-Policy (`'self'` only, no inline script),
  `frame-ancestors 'none'`, `nosniff`, a referrer policy, a permissions policy and HSTS, and
  caches hashed assets immutably. `vite preview` applies the same headers, so the end-to-end
  suite in CI runs under the production policy.
* After each successful production deployment, `.github/workflows/production-smoke.yml` runs the
  whole Playwright suite against the live URL.

## Consequences

* Every merge to `main` that touches `web/` changes the live site. The `web` CI job and the
  freshness check on `web/src/content/chp.json` are what stand between a pull request and
  learners; branch protection on `main` should require them.
* The site is static: no server code, no environment variables, no secrets, no cookies.
  Learner progress stays in each learner's browser (ADR 0010).
* The app still teaches content that no human has verified. Every entry says so, and the
  footer marks the site as a study aid, not an operational reference.
