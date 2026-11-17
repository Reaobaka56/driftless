import os
import subprocess

import pytest
from conftest import requires_ts

from driftless.discover import discover_source_files
from driftless.issues import Issue, dedupe
from driftless.pipeline import ScanConfig, scan_repository
from driftless.scanners.typescript import ScannerFailed, ScannerUnavailable, run_typescript_scan

CFG = ScanConfig(use_llm=False, registry_path="/nonexistent")


def rules(report, file=None):
    return {i.rule_id for i in report.issues if file is None or i.file == file}


@requires_ts
def test_typescript_tsx_and_javascript_are_parsed_and_analysed(ts_repo):
    r = scan_repository(str(ts_repo), CFG)
    assert {"ts-eval", "ts-command-injection", "ts-weak-hash", "ts-empty-catch", "ts-suppression",
            "ts-hardcoded-secret", "ts-async-foreach"} <= rules(r, "src/app.ts")
    assert rules(r, "src/Comp.tsx") == {"ts-xss-html-injection"}
    assert rules(r, "src/legacy.js") == {"ts-tls-verification-disabled", "ts-command-injection"}


@requires_ts
def test_no_false_positives_on_safe_code(ts_repo):
    r = scan_repository(str(ts_repo), CFG)
    assert not any(i.file == "src/clean.ts" for i in r.issues)           # label, commented catch
    assert not any(i.file == "src/app.ts" and i.start_line == 23 for i in r.issues)  # RegExp.exec


@requires_ts
def test_syntax_errors_reported_not_analysed_and_not_a_clean_success(ts_repo):
    r = scan_repository(str(ts_repo), CFG)
    assert any(p["file"] == "src/broken.ts" for p in r.parse_errors)
    assert not any(i.file == "src/broken.ts" for i in r.issues)
    ts_cap = next(c for c in r.capabilities if c.name == "typescript")
    assert ts_cap.status == "partial" and r.status == "partial"


@requires_ts
def test_ignored_directories_are_excluded(ts_repo):
    files = discover_source_files(ts_repo).files
    assert not any(f.startswith(("node_modules/", "dist/", "generated/")) for f in files)
    r = scan_repository(str(ts_repo), CFG)
    assert not any(i.file.startswith(("node_modules/", "dist/", "generated/")) for i in r.issues)


@requires_ts
def test_findings_are_normalized_unique_and_secrets_redacted(ts_repo):
    r = scan_repository(str(ts_repo), CFG)
    assert len({i.key for i in r.issues}) == len(r.issues)
    for i in r.issues:
        assert i.start_line <= i.end_line and 0 <= i.confidence <= 1 and i.remediation and i.evidence
        assert i.source == "ts-scanner"
    blob = " ".join(i.evidence for i in r.issues)
    assert "AKIAIOSFODNN7EXAMPLE" not in blob and "hunter2hunter2" not in blob


@requires_ts
def test_config_disables_rules_and_overrides_severity(ts_repo):
    cfg = ScanConfig(use_llm=False, registry_path="/nonexistent",
                     disabled_rules=frozenset({"ts-eval"}),
                     severity_overrides={"ts-weak-hash": "info"})
    r = scan_repository(str(ts_repo), cfg)
    assert "ts-eval" not in rules(r)
    assert next(i for i in r.issues if i.rule_id == "ts-weak-hash").severity == "info"
    with pytest.raises(ValueError):
        ScanConfig(severity_overrides={"x": "loud"})


def test_dedupe_keeps_first_and_is_sorted():
    a = Issue("r", "high", "b.ts", 3, 3, "d", "e", "x", 0.9, "ts-scanner")
    b = Issue("r", "low", "b.ts", 3, 3, "d2", "e", "x", 0.1, "llm:x")
    c = Issue("r", "low", "a.ts", 9, 9, "d", "e", "x", 0.5, "ts-scanner")
    out = dedupe([a, b, c])
    assert out == [c, a]


def test_issue_rejects_invalid_states():
    with pytest.raises(ValueError):
        Issue("r", "loud", "a.ts", 1, 1, "d", "e", "x", 0.5, "s")
    with pytest.raises(ValueError):
        Issue("r", "low", "a.ts", 5, 2, "d", "e", "x", 0.5, "s")
    with pytest.raises(ValueError):
        Issue("r", "low", "a.ts", 1, 1, "d", "e", "x", 1.5, "s")


# ---- failure honesty ----
def test_missing_node_is_unavailable_and_scan_fails_not_clean(ts_repo, monkeypatch):
    monkeypatch.setenv("DRIFTLESS_NODE", "/nonexistent/node")
    with pytest.raises(ScannerUnavailable):
        run_typescript_scan(ts_repo, ["src/app.ts"])
    r = scan_repository(str(ts_repo), CFG)
    assert r.status == "failed" and r.issues == []
    assert next(c for c in r.capabilities if c.name == "typescript").status == "unavailable"


def test_scanner_crash_is_failed_not_zero_findings(ts_repo):
    def boom(*a, **k):
        raise ScannerFailed("exploded")
    r = scan_repository(str(ts_repo), CFG, ts_runner=boom)
    assert r.status == "failed" and r.issues == []


def test_partial_when_other_capability_still_works(ts_repo):
    def boom(*a, **k):
        raise ScannerFailed("exploded")
    from conftest import REGISTRY
    r = scan_repository(str(ts_repo), ScanConfig(use_llm=False, registry_path=REGISTRY), ts_runner=boom)
    assert r.status == "partial"


def test_malformed_scanner_output_is_failure(ts_repo, monkeypatch):
    def fake_run(*a, **k):
        return subprocess.CompletedProcess(a, 0, stdout="not json", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("DRIFTLESS_NODE", "node")
    with pytest.raises(ScannerFailed):
        run_typescript_scan(ts_repo, ["src/app.ts"])


def test_no_ts_files_is_not_applicable_and_completes(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    r = scan_repository(str(tmp_path), CFG)
    assert r.status == "completed"
    assert next(c for c in r.capabilities if c.name == "typescript").status == "not_applicable"


# ---- discovery ----
def test_discovery_nested_gitignore_symlinks_size_and_generated(tmp_path):
    (tmp_path / "pkg/sub").mkdir(parents=True)
    (tmp_path / "pkg/.gitignore").write_text("secret.ts\nsub/\n")
    for f in ("a.ts", "pkg/b.ts", "pkg/secret.ts", "pkg/sub/c.ts", "types.d.ts", "x.min.js", "big.js"):
        (tmp_path / f).write_text("x\n" * (600_000 if f == "big.js" else 1))
    os.symlink(tmp_path / "a.ts", tmp_path / "link.ts")
    d = discover_source_files(tmp_path, max_file_bytes=1000)
    assert d.files == ["a.ts", "pkg/b.ts"]
    assert [s["file"] for s in d.skipped] == ["big.js"]


def test_registry_findings_are_normalized_into_issues():
    from conftest import FIXTURES, REGISTRY
    r = scan_repository(str(FIXTURES / "sample_repo"), ScanConfig(use_llm=False, registry_path=REGISTRY))
    assert r.status == "completed"
    (i,) = r.issues
    assert (i.rule_id, i.severity, i.file, i.start_line, i.source) == (
        "registry.stripe-2026-11-17-charge-source", "high", "app.py", 5, "registry")
    assert "payment_method" in i.remediation and "Charge.create" in i.evidence


def test_invalid_registry_is_reported_as_failed_capability_not_swallowed(tmp_path):
    reg = tmp_path / "reg"
    reg.mkdir()
    (reg / "bad.yaml").write_text("id: x\n")  # missing required fields
    (tmp_path / "a.py").write_text("x = 1\n")
    r = scan_repository(str(tmp_path), ScanConfig(use_llm=False, registry_path=str(reg)))
    assert next(c for c in r.capabilities if c.name == "registry").status == "failed"
    assert r.status == "failed"
