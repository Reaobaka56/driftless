import shutil
from pathlib import Path

from driftless.detect.python_ast import scan_python_repo
from driftless.fix.pipeline import fix_and_verify
from driftless.registry.loader import load_records, validate_records

ROOT = Path(__file__).resolve().parents[1]
REG = str(ROOT / "registry")
FIX = ROOT / "tests" / "fixtures" / "sample_repo"


def test_registry_valid():
    assert validate_records(REG)["errors"] == []


def test_scan_finds_only_affected_call():
    f = scan_python_repo(str(FIX), load_records(REG))
    assert len(f) == 1 and f[0].line == 5 and f[0].file == "app.py"


def test_scan_deterministic():
    recs = load_records(REG)
    assert scan_python_repo(str(FIX), recs) == scan_python_repo(str(FIX), recs)


def test_fix_rewrites_and_is_idempotent(tmp_path):
    repo = tmp_path / "r"
    shutil.copytree(FIX, repo)
    r = fix_and_verify("stripe-2026-11-17-charge-source", str(repo), registry=REG)
    assert r.status in ("success", "draft") and r.changed_files == ["app.py"]
    assert "payment_method=token" in (repo / "app.py").read_text()
    assert scan_python_repo(str(repo), load_records(REG)) == []
    r2 = fix_and_verify("stripe-2026-11-17-charge-source", str(repo), registry=REG)
    assert r2.message == "nothing to fix"


def test_dry_run_writes_nothing(tmp_path):
    repo = tmp_path / "r"
    shutil.copytree(FIX, repo)
    before = (repo / "app.py").read_text()
    fix_and_verify("stripe-2026-11-17-charge-source", str(repo), dry_run=True, registry=REG)
    assert (repo / "app.py").read_text() == before
