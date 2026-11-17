"""Scan worker.

Responsibilities: clone (read-only) -> run scanners -> persist findings -> report.
It must NOT fix code, write to the repository, create branches, commit, or open PRs.
TODO(fix-and-pr): a separate workflow consumes persisted scan_results and does that.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from driftless.pipeline import ScanConfig, ScanReport, scan_repository
from worker.ids import repo_hash


class ScanJobError(RuntimeError):
    pass


def clone_readonly(repo_url: str, dest: str) -> str:
    """Shallow https clone; returns HEAD sha. No hooks run, other transports refused."""
    if not repo_url.startswith("https://"):
        raise ScanJobError("only https:// repository URLs are accepted")
    env = {"PATH": os.environ.get("PATH", ""), "GIT_TERMINAL_PROMPT": "0",
           "HOME": os.environ.get("HOME", "/tmp")}
    base = ["git", "-c", "protocol.allow=never", "-c", "protocol.https.allow=always"]
    subprocess.run(base + ["clone", "--depth", "1", "--no-tags", "--", repo_url, dest],
                   check=True, timeout=180, capture_output=True, env=env)
    head = subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"], check=True,
                          timeout=30, capture_output=True, text=True, env=env)
    return head.stdout.strip()


def _default_conn():
    from worker.db import get_conn
    return get_conn()


def run_scan(repo_url: str, vendor: str, *,
             conn_factory: Callable = _default_conn,
             cloner: Callable[[str, str], str] = clone_readonly,
             scanner: Callable[..., ScanReport] = scan_repository,
             config: ScanConfig | None = None) -> dict:
    rh = repo_hash(repo_url)
    cfg = config or ScanConfig(vendor=vendor)
    with tempfile.TemporaryDirectory(prefix="driftless-scan-") as tmp:
        dest = str(Path(tmp) / "repo")
        sha = cloner(repo_url, dest)

        with conn_factory() as conn:  # claim: one row per (repo, vendor, commit)
            row = conn.execute(
                "INSERT INTO scan_results (repo_hash, vendor, commit_sha, status, findings) "
                "VALUES (%s, %s, %s, 'running', '[]'::jsonb) "
                "ON CONFLICT (repo_hash, vendor, commit_sha) "
                "DO UPDATE SET commit_sha = EXCLUDED.commit_sha RETURNING id, status",
                (rh, vendor, sha)).fetchone()
        if row["status"] == "completed":
            return {"status": "skipped", "reason": "already scanned at this commit"}

        try:
            report = scanner(dest, cfg)
            if report.status == "failed":
                raise ScanJobError("; ".join(f"{c.name}: {c.status} ({c.detail})"
                                             for c in report.capabilities if c.status != "ok"))
        except Exception as e:
            with conn_factory() as conn:
                conn.execute("UPDATE scan_results SET status = 'failed', error = %s, "
                             "scanned_at = NOW() WHERE id = %s", (str(e)[:500], row["id"]))
            raise

        with conn_factory() as conn:
            conn.execute(
                "UPDATE scan_results SET status = %s, findings = %s::jsonb, analysis = %s::jsonb, "
                "error = NULL, scanned_at = NOW() WHERE id = %s",
                (report.status, json.dumps([i.to_dict() for i in report.issues]),
                 json.dumps(report.persisted_analysis()), row["id"]))
    return {"status": report.status, "findings": len(report.issues),
            "llm": report.analysis.status}
