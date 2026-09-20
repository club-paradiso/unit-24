"""radiocorpus command-line interface. Every stage is a separate, resumable command; `run-canary`
chains them in the documented order."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print as rprint

from radiocorpus.config import PATHS
from radiocorpus.store import Store

app = typer.Typer(no_args_is_help=True, add_completion=False, help=__doc__)


def _store(db: Path | None) -> Store:
    PATHS.ensure()
    return Store(db or PATHS.db)


@app.command()
def init_db(db: Path | None = None) -> None:
    """Create the SQLite database and schema."""
    s = _store(db)
    rprint(f"initialized {s.path}")


@app.command()
def ingest_registry(adapter: str, path: Path, db: Path | None = None) -> None:
    """Load a registry snapshot (adapters: fbi_cde_frontend, curated, delimited)."""
    from radiocorpus.registry.ingest import ingest_registry as _ing

    rprint(_ing(_store(db), adapter, path).stats)


@app.command()
def resolve(registry: str = "FBI_CDE_FRONTEND_2018", target: str = "CURATED_CANARY", db: Path | None = None) -> None:
    """Seed canonical agencies from the curated registry and link other registries to them."""
    from radiocorpus.registry.resolve import Resolver

    s = _store(db)
    r = Resolver(s)
    rprint("seed:", r.seed_curated(target).__dict__)
    rep = r.resolve_registry(registry, target_registry=target)
    s.commit()
    rprint({k: v for k, v in rep.__dict__.items() if k != "examples"})
    for e in rep.examples:
        rprint("  ", e)


@app.command()
def discover(
    leads: Path = PATHS.canary / "discovery_leads.jsonl", registry: str = "CURATED_CANARY", force: bool = False, db: Path | None = None
) -> None:
    """Official-domain + document discovery from recorded search results."""
    from radiocorpus.discovery.stage import discover_from_recorded

    rprint(discover_from_recorded(_store(db), leads, registry=registry, force=force).stats)


@app.command()
def acquire(limit: int | None = None, force: bool = False, db: Path | None = None) -> None:
    """Fetch official candidate documents (robots-aware; records egress blocks instead of failing)."""
    from radiocorpus.acquisition.fetch import acquire as _acq

    rprint(_acq(_store(db), limit=limit, force=force).stats)


@app.command()
def load_fixtures(db: Path | None = None) -> None:
    """Load the synthetic fixture agencies and documents (state ZZ)."""
    from radiocorpus.fixtures import load_fixtures as _lf

    rprint(_lf(_store(db), PATHS.fixtures, PATHS.documents))


@app.command()
def extract(force: bool = False, db: Path | None = None) -> None:
    """Deterministic candidate-fact extraction over acquired documents."""
    from radiocorpus.extraction.stage import extract_all

    rprint(extract_all(_store(db), force=force).stats)


@app.command()
def classify_sources(db: Path | None = None) -> None:
    """Assign source quality / temporal status."""
    from radiocorpus.provenance.classify import classify_all

    rprint(classify_all(_store(db)).stats)


@app.command()
def validate(db: Path | None = None) -> None:
    from radiocorpus.validation.rules import validate_all

    rprint(validate_all(_store(db)).stats)


@app.command()
def crosscheck(db: Path | None = None) -> None:
    """Cross-source comparison and conflict detection/resolution."""
    from radiocorpus.conflicts.detect import detect_conflicts

    rprint(detect_conflicts(_store(db)).stats)


@app.command()
def assign(db: Path | None = None) -> None:
    """Verification status + training eligibility."""
    from radiocorpus.eligibility.policy import assign_all

    rprint(assign_all(_store(db)).stats)


@app.command()
def export(out: Path = PATHS.normalized, registry: str | None = "CURATED_CANARY", include_fixtures: bool = False, db: Path | None = None) -> None:
    from radiocorpus.export import export_all

    rprint(export_all(_store(db), out, registry_filter=registry, include_fixtures=include_fixtures))


@app.command()
def stats(registry: str | None = None, include_fixtures: bool = False, out: Path | None = None, db: Path | None = None) -> None:
    from radiocorpus.stats import corpus_stats

    st = corpus_stats(_store(db), registry_filter=registry, include_fixtures=include_fixtures)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n")
    rprint(json.dumps(st, indent=2, sort_keys=True))


@app.command()
def check_invariants(db: Path | None = None) -> None:
    from radiocorpus.invariants import check_all

    res = check_all(_store(db))
    from radiocorpus.config import PATHS
    from radiocorpus.report_consistency import check_audit_metrics, check_report
    from radiocorpus.snapshot_check import check_snapshot

    res["normalized_snapshot"] = check_snapshot(PATHS.root / "data/normalized")
    res["fixture_snapshot"] = check_snapshot(PATHS.root / "data/normalized/fixtures")
    res["report_consistency"] = check_report(PATHS.root)
    res["audit_metrics_consistency"] = check_audit_metrics(PATHS.root)
    bad = {k: v for k, v in res.items() if v}
    for k, v in res.items():
        rprint(f"[{'red' if v else 'green'}]{k}: {len(v)} violation(s)")
        for x in v[:10]:
            rprint("   ", x)
    raise typer.Exit(code=1 if bad else 0)


@app.command()
def canary_report(out: Path = Path("docs/canary-report.md"), db: Path | None = None) -> None:
    from radiocorpus.report import render_markdown

    md = render_markdown(_store(db))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    rprint(f"wrote {out}")


@app.command()
def explain(fact_id: str, db: Path | None = None) -> None:
    """Why is this fact the expected answer? Prints evidence only."""
    from radiocorpus.eligibility.policy import explain as _explain

    rprint(json.dumps(_explain(_store(db), fact_id), indent=2, default=str))


@app.command()
def run_canary(db: Path | None = None, skip_acquire: bool = False, force: bool = False) -> None:
    """Reproduce the whole canary pipeline end to end."""
    from radiocorpus.acquisition.fetch import acquire as _acq
    from radiocorpus.conflicts.detect import detect_conflicts
    from radiocorpus.discovery.stage import discover_from_recorded
    from radiocorpus.eligibility.policy import assign_all
    from radiocorpus.export import export_all
    from radiocorpus.extraction.stage import extract_all
    from radiocorpus.fixtures import load_fixtures as _lf
    from radiocorpus.invariants import check_all
    from radiocorpus.provenance.classify import classify_all
    from radiocorpus.registry.ingest import ingest_registry as _ing
    from radiocorpus.registry.resolve import Resolver
    from radiocorpus.report import render_markdown
    from radiocorpus.stats import corpus_stats
    from radiocorpus.validation.rules import validate_all

    s = _store(db)
    rprint("[bold]1 registry ingestion")
    rprint(_ing(s, "curated", PATHS.canary / "canary_seed.jsonl").stats)
    rprint(_ing(s, "fbi_cde_frontend", PATHS.raw / "fbi_cde_frontend" / "agencies-by-state.json.gz").stats)
    rprint("[bold]2 entity resolution")
    r = Resolver(s)
    r.seed_curated("CURATED_CANARY")
    rep = r.resolve_registry("FBI_CDE_FRONTEND_2018")
    s.commit()
    rprint({k: v for k, v in rep.__dict__.items() if k != "examples"})
    rprint("[bold]3/4 discovery")
    rprint(discover_from_recorded(s, PATHS.canary / "discovery_leads.jsonl", force=force).stats)
    rprint("[bold]5 acquisition")
    rprint("skipped" if skip_acquire else _acq(s, force=force).stats)
    rprint("[bold]5b fixtures")
    rprint(_lf(s, PATHS.fixtures, PATHS.documents))
    rprint("[bold]6/7 extraction")
    rprint(extract_all(s, force=force).stats)
    rprint("[bold]8 source classification + validation")
    rprint(classify_all(s).stats)
    rprint(validate_all(s).stats)
    rprint("[bold]9/10 conflicts")
    rprint(detect_conflicts(s).stats)
    rprint("[bold]11 eligibility")
    rprint(assign_all(s).stats)
    rprint("[bold]12 export + stats + invariants")
    rprint(export_all(s, PATHS.normalized, registry_filter="CURATED_CANARY"))
    rprint(export_all(s, PATHS.normalized / "fixtures", registry_filter="FIXTURE", include_fixtures=True))
    st = corpus_stats(s, registry_filter="CURATED_CANARY")
    (PATHS.normalized / "stats_canary.json").write_text(json.dumps(st, indent=2, sort_keys=True) + "\n")
    stf = corpus_stats(s, registry_filter="FIXTURE", include_fixtures=True)
    (PATHS.normalized / "stats_fixtures.json").write_text(json.dumps(stf, indent=2, sort_keys=True) + "\n")
    st_all = corpus_stats(s)
    (PATHS.normalized / "stats_all.json").write_text(json.dumps(st_all, indent=2, sort_keys=True) + "\n")
    inv = check_all(s)
    for k, v in inv.items():
        rprint(f"[{'red' if v else 'green'}]invariant {k}: {len(v)} violation(s)")
    Path("docs").mkdir(exist_ok=True)
    Path("docs/canary-report.md").write_text(render_markdown(s))
    rprint("[bold]done -> docs/canary-report.md, data/normalized/")


if __name__ == "__main__":
    app()
