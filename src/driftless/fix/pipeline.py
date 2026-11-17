from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from driftless.detect.python_ast import iter_py_files, scan_python_repo
from driftless.fix.recipes import RecipeError, RenameKeywordParams, apply_to_file
from driftless.registry.loader import load_records
from driftless.verify.score import compute_confidence


@dataclass
class FixResult:
    status: str  # success | draft | failed
    confidence: float = 0.0
    changed_files: list[str] = field(default_factory=list)
    message: str = ""
    skipped: list[str] = field(default_factory=list)


def _run_tests(repo_path: str) -> bool | None:
    if not (Path(repo_path) / "tests").exists():
        return None
    try:
        r = subprocess.run(["python", "-m", "pytest", "-q", "-x"], cwd=repo_path,
                           capture_output=True, timeout=300, check=False)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def fix_and_verify(record_id: str, repo_path: str, strategy: str = "recipe",
                   dry_run: bool = False, registry: str = "registry") -> FixResult:
    recs = load_records(registry, record_id=record_id)
    if not recs:
        return FixResult("failed", message=f"record {record_id} not found or not reviewed")
    rec = recs[0]
    if strategy != "recipe":
        return FixResult("failed", message="only the 'recipe' strategy is implemented")
    try:
        params = RenameKeywordParams.from_record(rec)
    except RecipeError as e:
        return FixResult("failed", message=str(e))

    root = Path(repo_path).resolve()
    originals: dict[Path, str] = {}
    changed: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []
    for py in iter_py_files(repo_path):
        rel = py.relative_to(root).as_posix()
        before = py.read_text(encoding="utf-8", errors="replace")
        res = apply_to_file(py, root, params, dry_run=dry_run)
        skipped += [f"{rel}: {s}" for s in res.skipped if res.matches]
        if res.status == "error":
            if "syntax error" not in (res.error or ""):  # unparseable files are not ours
                errors.append(f"{rel}: {res.error}")
        elif res.status == "changed":
            changed.append(rel)
            originals[py] = before

    def revert() -> None:
        for p, code in originals.items():
            p.write_text(code, encoding="utf-8")

    if errors:
        if not dry_run:
            revert()
        return FixResult("failed", changed_files=changed, skipped=skipped,
                         message="; ".join(errors) + " (changes reverted)")
    if not changed:
        msg = "unsafe/ambiguous calls left untouched" if skipped else "nothing to fix"
        return FixResult("draft" if skipped else "success", 1.0 if not skipped else 0.0,
                         [], msg, skipped)
    if dry_run:
        return FixResult("draft", 0.0, changed, "dry run, no files written", skipped)

    clean = not scan_python_repo(repo_path, [rec]) or bool(skipped)
    tests = _run_tests(repo_path)
    conf = compute_confidence(not skipped and clean, tests, parses=True)
    if tests is False or (not skipped and not clean):
        revert()
        return FixResult("failed", conf, changed, "verification failed, changes reverted", skipped)
    status = "success" if conf >= 0.8 and not skipped else "draft"
    return FixResult(status, conf, changed, "", skipped)
