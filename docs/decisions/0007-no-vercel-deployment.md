# ADR 0007 — this repository is not a Vercel deployment target

**Status:** accepted (2026-09-21)

## Context

A Vercel project (`club-paradiso/unit-24`) is connected to this repository and builds every
pushed commit. Every build fails identically:

```
errorCode:    PYTHON_ENTRYPOINT_NOT_FOUND
errorMessage: No python entrypoint found in default locations, but found potential entrypoints:
                src/radiocorpus/cli.py (variable: app)
              Add this to your pyproject.toml:
              [tool.vercel]
              entrypoint = "src.radiocorpus.cli:app"
errorStep:    buildStep
```

Vercel auto-detected `framework: "python"` from `pyproject.toml` and looked for a web
entrypoint to host as a function. The failure is correct: there is no web entrypoint. This
repository is a research corpus and an offline pipeline. It has no HTTP surface, no static
site and nothing to serve.

The remedy Vercel suggests must not be applied. `src/radiocorpus/cli.py:app` is a **Typer
command-line application**, not an ASGI or WSGI application. Pointing a serverless HTTP
function at it would not produce a working deployment, and to the extent it produced
anything it would expose the corpus research and ingestion CLI over the public internet.
That is a larger problem than a red check.

## Decision

Disable Git-triggered deployments for this repository, declared in the repository so the
intent is version-controlled and visible in review rather than hidden in dashboard state:

```json
{ "git": { "deploymentEnabled": false } }
```

Per Vercel's Git configuration reference, `deploymentEnabled: false` prevents any branch
from triggering a deployment.

## Consequences

* No Vercel deployment is created for any branch, so no deployment status is reported on
  pull requests. The repository's own CI (`.github/workflows/ci.yml`: pytest, ruff,
  `radiocorpus check-invariants`) is unaffected and remains the only gate.
* The Vercel project is left in place and untouched; nothing in the team account was
  deleted or reconfigured. Re-enabling is a one-line revert.
* When a consumer application is eventually built, it will be a separate deployable surface
  with a real web entrypoint. That is when this decision is revisited — by adding the
  surface, not by aiming Vercel at the CLI.
