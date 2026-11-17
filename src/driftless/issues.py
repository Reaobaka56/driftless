"""One normalized issue schema shared by every scanner and the LLM layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

SEVERITIES = ("critical", "high", "medium", "low", "info")


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: str
    file: str  # repo-relative, forward slashes
    start_line: int
    end_line: int
    description: str
    evidence: str
    remediation: str
    confidence: float
    source: str  # e.g. "ts-scanner", "registry", "llm:anthropic"

    def __post_init__(self) -> None:  # make invalid states hard to represent
        if self.severity not in SEVERITIES:
            raise ValueError(f"invalid severity: {self.severity!r}")
        if not (self.rule_id and self.file and self.description and self.evidence):
            raise ValueError("rule_id, file, description and evidence are required")
        if not 1 <= self.start_line <= self.end_line:
            raise ValueError(f"invalid line range {self.start_line}-{self.end_line}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence}")

    @property
    def key(self) -> tuple[str, str, int, int]:
        return (self.rule_id, self.file, self.start_line, self.end_line)

    def to_dict(self) -> dict:
        return asdict(self)

    def with_severity(self, severity: str) -> Issue:
        return replace(self, severity=severity)


def dedupe(issues: list[Issue]) -> list[Issue]:
    """Keep the first issue per key (callers list deterministic sources first)."""
    seen: dict[tuple, Issue] = {}
    for i in issues:
        seen.setdefault(i.key, i)
    return sorted(seen.values(), key=lambda i: (i.file, i.start_line, i.rule_id))
