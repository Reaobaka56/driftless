"""Scan pipeline: deterministic scanners -> LLM analysis with fallback -> one report.

Read-only by construction: nothing here writes to the scanned repository.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from driftless.discover import TS_EXTENSIONS, Discovery, discover_source_files
from driftless.issues import SEVERITIES, Issue, dedupe
from driftless.llm.chain import AnalysisOutcome, LLMPolicy, analyze_with_fallback
from driftless.llm.prompt import SYSTEM_PROMPT, build_user_prompt, select_files
from driftless.llm.providers import LLMProvider, providers_from_env
from driftless.scanners.registry_calls import scan_registry_issues
from driftless.scanners.typescript import (
    ScannerFailed,
    ScannerUnavailable,
    TSScanResult,
    run_typescript_scan,
)


@dataclass(frozen=True)
class ScanConfig:
    disabled_rules: frozenset[str] = frozenset()
    severity_overrides: Mapping[str, str] = field(default_factory=dict)
    max_file_bytes: int = 1_000_000
    ts_timeout: float = 120.0
    use_llm: bool = True
    registry_path: str = "registry"
    vendor: str | None = None

    def __post_init__(self) -> None:
        for rule, sev in self.severity_overrides.items():
            if sev not in SEVERITIES:
                raise ValueError(f"invalid severity {sev!r} for rule {rule!r}")

    @classmethod
    def from_file(cls, path: str) -> ScanConfig:
        d = json.loads(Path(path).read_text())
        unknown = set(d) - {"disabled_rules", "severity_overrides", "max_file_bytes",
                            "use_llm", "registry_path", "vendor"}
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        d["disabled_rules"] = frozenset(d.get("disabled_rules", []))
        return cls(**d)


@dataclass
class Capability:
    name: str
    status: str  # ok | partial | unavailable | failed | not_applicable
    detail: str = ""


@dataclass
class ScanReport:
    status: str  # completed | partial | failed
    issues: list[Issue]
    capabilities: list[Capability]
    analysis: AnalysisOutcome
    parse_errors: list[dict] = field(default_factory=list)
    skipped_files: list[dict] = field(default_factory=list)
    files_scanned: int = 0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "issues": [i.to_dict() for i in self.issues],
            "capabilities": [c.__dict__ for c in self.capabilities],
            "analysis": self.analysis.to_dict(),
            "parse_errors": self.parse_errors,
            "skipped_files": self.skipped_files,
            "files_scanned": self.files_scanned,
        }

    def persisted_analysis(self) -> dict:
        d = self.to_dict()
        d.pop("issues")
        return d


TSRunner = Callable[[Path, list[str], ScanConfig, list[dict]], TSScanResult]


def _default_ts_runner(root, files, cfg, skipped):
    return run_typescript_scan(root, files, timeout=cfg.ts_timeout, skipped=skipped)


def _apply_config(issues: list[Issue], cfg: ScanConfig) -> list[Issue]:
    kept = [i for i in issues if i.rule_id not in cfg.disabled_rules]
    return [i.with_severity(cfg.severity_overrides[i.rule_id])
            if i.rule_id in cfg.severity_overrides else i for i in kept]


def scan_repository(
    repo_path: str, config: ScanConfig = ScanConfig(), *,
    providers: Sequence[LLMProvider] | None = None,
    llm_policy: LLMPolicy = LLMPolicy(),
    ts_runner: TSRunner = _default_ts_runner,
    sleep: Callable[[float], None] | None = None,
) -> ScanReport:
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {repo_path}")

    caps: list[Capability] = []
    issues: list[Issue] = []
    parse_errors: list[dict] = []
    skipped: list[dict] = []
    files_scanned = 0

    # 1. deterministic: registry-driven Python call sites
    try:
        reg = scan_registry_issues(root, config.registry_path, config.vendor)
        issues += reg
        caps.append(Capability("registry", "ok" if Path(config.registry_path).is_dir()
                               else "not_applicable", f"{len(reg)} findings"))
    except Exception as e:  # noqa: BLE001 - invalid registry must be visible, not fatal
        caps.append(Capability("registry", "failed", f"{type(e).__name__}: {e}"))

    # 2. deterministic: TypeScript/JavaScript scanner
    ts_disc: Discovery = discover_source_files(root, TS_EXTENSIONS, max_file_bytes=config.max_file_bytes)
    skipped += ts_disc.skipped
    if not ts_disc.files:
        caps.append(Capability("typescript", "not_applicable", "no TS/JS files"))
    else:
        try:
            r = ts_runner(root, ts_disc.files, config, ts_disc.skipped)
            issues += r.issues
            parse_errors += r.parse_errors
            skipped = list(r.skipped)
            files_scanned += r.scanned
            unanalysed = len(ts_disc.files) - r.scanned
            caps.append(Capability(
                "typescript", "ok" if unanalysed == 0 else "partial",
                f"{r.scanned}/{len(ts_disc.files)} files analysed"
                + (f", {len(r.parse_errors)} parse errors" if r.parse_errors else "")))
        except ScannerUnavailable as e:
            caps.append(Capability("typescript", "unavailable", str(e)))
        except ScannerFailed as e:
            caps.append(Capability("typescript", "failed", str(e)))

    issues = dedupe(_apply_config(issues, config))

    # 3. LLM analysis with fallback (never required for completion)
    analysis = AnalysisOutcome(status="skipped")
    if config.use_llm:
        py_files = discover_source_files(root, (".py",), max_file_bytes=config.max_file_bytes).files
        files = select_files(root, ts_disc.files + py_files, {i.file for i in issues})
        provs = providers if providers is not None else providers_from_env(os.environ)
        kwargs = {"sleep": sleep} if sleep else {}
        analysis = analyze_with_fallback(provs, SYSTEM_PROMPT, build_user_prompt(files), files,
                                         policy=llm_policy, **kwargs)
        # deterministic issues are listed first, so they win duplicate keys
        issues = dedupe(issues + _apply_config(analysis.issues, config))
    if config.use_llm:
        caps.append(Capability(
            "llm", "ok" if analysis.status == "llm" else
            ("not_applicable" if analysis.status == "skipped" else "unavailable"),
            f"provider={analysis.provider}" if analysis.provider else
            "no LLM provider produced a result; deterministic analysis only"))

    applicable = [c for c in caps if c.name != "llm" and c.status != "not_applicable"]
    if applicable and all(c.status in ("failed", "unavailable") for c in applicable):
        status = "failed"
    elif any(c.status in ("failed", "unavailable", "partial") for c in applicable):
        status = "partial"
    else:
        status = "completed"
    return ScanReport(status, issues, caps, analysis, parse_errors, skipped, files_scanned)
