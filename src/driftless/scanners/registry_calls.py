"""Adapter: registry-driven Python call-site findings -> normalized Issues."""
from __future__ import annotations

from pathlib import Path

from driftless.detect.python_ast import scan_python_repo
from driftless.issues import Issue
from driftless.registry.loader import load_records

_LEGACY_SEVERITY = {"error": "high", "warning": "medium", "info": "info"}


def scan_registry_issues(root: Path, registry_path: str, vendor: str | None) -> list[Issue]:
    if not Path(registry_path).is_dir():
        return []
    records = {r.id: r for r in load_records(registry_path, vendor=vendor)}
    out: list[Issue] = []
    for f in scan_python_repo(str(root), list(records.values())):
        rec = records[f.record_id]
        try:
            lines = (root / f.file).read_text(encoding="utf-8", errors="replace").splitlines()
            evidence = lines[f.line - 1].strip()[:200]
        except (OSError, IndexError):
            evidence = f.symbol
        out.append(Issue(
            rule_id=f"registry.{rec.id}",
            severity=_LEGACY_SEVERITY.get(f.severity, f.severity), file=f.file,
            start_line=f.line, end_line=f.line,
            description=(f"{f.symbol} uses '{rec.affects.get('param')}' which the vendor "
                         f"changes ({rec.type}) effective {rec.effective}."),
            evidence=evidence or f.symbol, remediation=rec.migration_note,
            confidence=f.confidence, source="registry"))
    return out
