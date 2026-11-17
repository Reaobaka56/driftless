import ast
import hashlib
import shutil
import subprocess
from functools import partial
from pathlib import Path

import pytest
from conftest import REGISTRY, ROOT, requires_ts

from driftless.llm import errors as E
from driftless.pipeline import ScanConfig, scan_repository
from worker import tasks
from worker.ids import repo_hash

URL = "https://github.com/example/repo"


class Store:
    def __init__(self):
        self.rows, self.sql = {}, []


class FakeConn:
    def __init__(self, store):
        self.s = store

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self.s.sql.append(sql)
        if sql.startswith("INSERT INTO scan_results"):
            key = params[:3]
            row = self.s.rows.setdefault(key, {"id": len(self.s.rows) + 1, "status": "running"})
            return type("R", (), {"fetchone": lambda _: dict(row)})()
        if sql.startswith("UPDATE scan_results SET status = 'failed'"):
            self._by_id(params[1]).update(status="failed", error=params[0])
        elif sql.startswith("UPDATE scan_results SET status = %s"):
            self._by_id(params[3]).update(status=params[0], findings=params[1], analysis=params[2])
        return None

    def _by_id(self, i):
        return next(r for r in self.s.rows.values() if r["id"] == i)


class DeadLLM:
    name, configured = "dead", True

    def complete(self, *a, **k):
        raise E.Unavailable("down")


def fake_cloner(src):
    def clone(url, dest):
        shutil.copytree(src, dest)
        return "deadbeef"
    return clone


def tree_hash(root: Path):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def job(store, src, registry=REGISTRY):
    scanner = partial(scan_repository, providers=[DeadLLM()], sleep=lambda s: None)
    return tasks.run_scan(URL, "stripe", conn_factory=lambda: FakeConn(store),
                          cloner=fake_cloner(src), scanner=scanner,
                          config=ScanConfig(registry_path=registry, vendor="stripe"))


@requires_ts
def test_scan_completes_and_persists_findings_even_when_every_llm_fails(ts_repo):
    store = Store()
    out = job(store, ts_repo)
    row = next(iter(store.rows.values()))
    assert out["status"] == "partial" and out["llm"] == "unavailable"   # broken.ts => partial, honestly
    assert row["status"] == "partial" and '"ts-eval"' in row["findings"]
    assert '"unavailable"' in row["analysis"] and "dead" in row["analysis"]
    assert next(iter(store.rows)) == (repo_hash(URL), "stripe", "deadbeef")


@requires_ts
def test_clean_repo_completes(tmp_path):
    src = tmp_path / "src"
    (src / "a").mkdir(parents=True)
    (src / "a/ok.ts").write_text("export const x = 1;\n")
    store = Store()
    assert job(store, src)["status"] == "completed"


@requires_ts
def test_completed_scan_is_idempotent_per_commit(ts_repo):
    store = Store()
    job(store, ts_repo)
    store.rows[next(iter(store.rows))]["status"] = "completed"
    assert job(store, ts_repo)["status"] == "skipped"
    assert sum(q.startswith("UPDATE scan_results SET status = %s") for q in store.sql) == 1


def test_scanner_failure_is_recorded_and_reraised(tmp_path):
    src = tmp_path / "s"
    src.mkdir()
    (src / "a.ts").write_text("export {};\n")

    def broken(dest, cfg):
        raise RuntimeError("scanner blew up")
    store = Store()
    with pytest.raises(RuntimeError):
        tasks.run_scan(URL, "stripe", conn_factory=lambda: FakeConn(store),
                       cloner=fake_cloner(src), scanner=broken)
    assert next(iter(store.rows.values()))["status"] == "failed"


def test_all_scanners_failed_is_a_failed_job_not_an_empty_success(tmp_path, monkeypatch):
    src = tmp_path / "s"
    src.mkdir()
    (src / "a.ts").write_text("export {};\n")
    monkeypatch.setenv("DRIFTLESS_NODE", "/nonexistent/node")
    store = Store()
    with pytest.raises(tasks.ScanJobError):
        job(store, src, registry="/nonexistent")       # nothing else can run
    assert next(iter(store.rows.values()))["status"] == "failed"


def test_unavailable_ts_scanner_with_working_registry_scan_is_recorded_partial(tmp_path, monkeypatch):
    src = tmp_path / "s"
    src.mkdir()
    (src / "a.ts").write_text("export {};\n")
    monkeypatch.setenv("DRIFTLESS_NODE", "/nonexistent/node")
    store = Store()
    assert job(store, src)["status"] == "partial"
    assert '"unavailable"' in next(iter(store.rows.values()))["analysis"]


@requires_ts
def test_worker_detects_but_never_modifies_the_scanned_repo(ts_repo):
    (ts_repo / "pay.py").write_text("import stripe\nstripe.Charge.create(source=t)\n")
    checks = {}

    def checking_scanner(dest, cfg):
        before = tree_hash(Path(dest))
        report = scan_repository(dest, cfg, providers=[DeadLLM()], sleep=lambda s: None)
        checks["unchanged"] = tree_hash(Path(dest)) == before
        checks["git_dir"] = (Path(dest) / ".git").exists()
        return report

    store = Store()
    tasks.run_scan(URL, "stripe", conn_factory=lambda: FakeConn(store), cloner=fake_cloner(ts_repo),
                   scanner=checking_scanner, config=ScanConfig(registry_path=REGISTRY, vendor="stripe"))
    row = next(iter(store.rows.values()))
    assert '"registry.stripe-2026-11-17-charge-source"' in row["findings"]   # detected...
    assert checks == {"unchanged": True, "git_dir": False}                   # ...not fixed


def test_worker_has_no_fix_branch_commit_or_pr_capability():
    tree = ast.parse((ROOT / "worker/tasks.py").read_text())
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and m.startswith(("driftless.fix", "driftless.deliver")) for m in imported)
    consts = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    forbidden = {"push", "checkout", "commit", "branch", "switch", "add", "apply", "merge",
                 "rebase", "reset", "tag", "pr", "gh"}
    assert not (consts & forbidden), consts & forbidden
    git_verbs = {c for c in consts if c in {"clone", "rev-parse"}}
    assert git_verbs == {"clone", "rev-parse"}


def test_clone_uses_only_readonly_git_commands(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")
    monkeypatch.setattr(tasks.subprocess, "run", fake_run)
    assert tasks.clone_readonly(URL, str(tmp_path / "d")) == "abc123"
    verbs = [c[c.index("clone")] if "clone" in c else c[3] for c in calls]
    assert verbs == ["clone", "rev-parse"]
    assert "--" in calls[0] and calls[0].index("--") < calls[0].index(URL)  # no option injection


@pytest.mark.parametrize("url", ["file:///etc", "ext::sh -c id", "git@github.com:a/b.git",
                                 "--upload-pack=evil", "http://x/y"])
def test_clone_rejects_non_https(url, tmp_path):
    with pytest.raises(tasks.ScanJobError):
        tasks.clone_readonly(url, str(tmp_path / "d"))


def test_migration_files_pair_up():
    m = ROOT / "migrations"
    assert (m / "002_scan_analysis.sql").exists() and (m / "002_down.sql").exists()
