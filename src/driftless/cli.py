import json

import typer

from driftless.detect.python_ast import scan_python_repo
from driftless.fix.pipeline import fix_and_verify
from driftless.metrics.report import get_stats
from driftless.pipeline import ScanConfig, scan_repository
from driftless.registry.loader import load_records, validate_records

app = typer.Typer(help="Driftless: self-maintaining API integrations", no_args_is_help=True)


@app.command("registry-validate")
def registry_validate(path: str = "registry"):
    res = validate_records(path)
    if res["errors"]:
        typer.echo(f"Validation failed: {res['errors']}", err=True)
        raise typer.Exit(2)
    typer.echo(f"Validated {len(res['valid'])} records.")


@app.command()
def scan(repo_path: str = typer.Argument("."), vendor: str | None = None, format: str = "text",
         registry: str = "registry"):
    findings = scan_python_repo(repo_path, load_records(registry, vendor=vendor))
    if format == "json":
        typer.echo(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        for f in findings:
            typer.echo(f"{f.file}:{f.line} {f.symbol} (record: {f.record_id})")
    raise typer.Exit(1 if findings else 0)


@app.command()
def analyze(repo_path: str = typer.Argument("."), format: str = "text",
            config: str | None = None, no_llm: bool = False, registry: str = "registry"):
    """Full read-only analysis: registry + TypeScript scanner + optional LLM (with fallback)."""
    cfg = ScanConfig.from_file(config) if config else ScanConfig(registry_path=registry)
    if no_llm:
        from dataclasses import replace
        cfg = replace(cfg, use_llm=False)
    report = scan_repository(repo_path, cfg)
    if format == "json":
        typer.echo(json.dumps(report.to_dict(), indent=2))
    else:
        for i in report.issues:
            typer.echo(f"{i.file}:{i.start_line} [{i.severity}] {i.rule_id} ({i.source}) {i.description}")
        for c in report.capabilities:
            typer.echo(f"capability {c.name}: {c.status} {c.detail}", err=True)
    raise typer.Exit(3 if report.status == "failed" else (1 if report.issues else 0))


@app.command()
def fix(record_id: str, repo_path: str = typer.Argument("."), strategy: str = "recipe",
        dry_run: bool = False, registry: str = "registry"):
    res = fix_and_verify(record_id, repo_path, strategy, dry_run, registry)
    typer.echo(f"{res.status} confidence={res.confidence} files={res.changed_files} {res.message}")
    raise typer.Exit(3 if res.status == "failed" else 0)


@app.command()
def stats(since: str | None = None):
    typer.echo(get_stats(since))


if __name__ == "__main__":
    app()
