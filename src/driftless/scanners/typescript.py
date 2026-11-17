"""Python wrapper around scanners/ts/scan.mjs (TypeScript Compiler API)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from driftless.issues import Issue

SCRIPT = Path(__file__).parent / "ts" / "scan.mjs"


class ScannerUnavailable(RuntimeError):
    """The scanner cannot run here (no node / no typescript package)."""


class ScannerFailed(RuntimeError):
    """The scanner ran but did not produce a trustworthy result."""


@dataclass
class TSScanResult:
    issues: list[Issue] = field(default_factory=list)
    parse_errors: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    scanned: int = 0


def run_typescript_scan(root: str | Path, files: list[str], *, timeout: float = 120.0,
                        skipped: list[dict] | None = None) -> TSScanResult:
    if not files:
        return TSScanResult(skipped=list(skipped or []))
    node = os.environ.get("DRIFTLESS_NODE") or shutil.which("node")
    if not node:
        raise ScannerUnavailable("node executable not found (set DRIFTLESS_NODE)")
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "HOME", "DRIFTLESS_TYPESCRIPT_PATH", "SYSTEMROOT")}
    payload = json.dumps({"root": str(Path(root).resolve()), "files": files})
    try:
        proc = subprocess.run([node, str(SCRIPT)], check=False, input=payload, capture_output=True,
                              text=True, timeout=timeout, env=env, cwd=SCRIPT.parent)
    except FileNotFoundError as e:
        raise ScannerUnavailable(f"cannot execute node: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise ScannerFailed(f"typescript scanner timed out after {timeout}s") from e

    if proc.returncode == 3 and "typescript_not_found" in proc.stdout:
        raise ScannerUnavailable(
            f"'typescript' npm package not installed; run `npm install` in {SCRIPT.parent}")
    if proc.returncode != 0:
        raise ScannerFailed(f"scanner exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    try:
        data = json.loads(proc.stdout)
        issues = [Issue(source="ts-scanner", **i) for i in data["issues"]]
        return TSScanResult(issues, data["parseErrors"],
                            list(skipped or []) + data["skipped"], int(data["scanned"]))
    except (ValueError, KeyError, TypeError) as e:
        raise ScannerFailed(f"malformed scanner output: {e}") from e
