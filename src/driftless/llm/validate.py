"""Model output is untrusted data: parse, validate, and ground every finding."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from driftless.issues import SEVERITIES, Issue
from driftless.llm.errors import InvalidOutput

MAX_FINDINGS = 50
MAX_LLM_CONFIDENCE = 0.8
_RULE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass
class Validated:
    issues: list[Issue] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


def _clean(s: object, limit: int) -> str:
    return _CTRL.sub("", s).strip()[:limit] if isinstance(s, str) else ""


def _norm(s: str) -> str:
    return " ".join(s.split())


def _extract_json(raw: str):
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except ValueError:
        a, b = text.find("{"), text.rfind("}")
        if a != -1 and b > a:
            try:
                return json.loads(text[a:b + 1])
            except ValueError:
                pass
    raise InvalidOutput("model output is not valid JSON")


def validate_findings(raw: str, files: dict[str, str], source: str) -> Validated:
    data = _extract_json(raw)
    items = data.get("findings") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise InvalidOutput("'findings' must be a list")
    out = Validated()
    for n, item in enumerate(items):
        if n >= MAX_FINDINGS:
            out.rejected.append(f"finding limit {MAX_FINDINGS} exceeded")
            break
        try:
            out.issues.append(_to_issue(item, files, source))
        except (ValueError, TypeError, KeyError) as e:
            out.rejected.append(f"#{n}: {e}")
    if items and not out.issues:
        raise InvalidOutput(f"all {len(items)} findings failed validation")
    return out


def _to_issue(item: object, files: dict[str, str], source: str) -> Issue:
    if not isinstance(item, dict):
        raise ValueError("not an object")
    rule = _clean(item.get("rule_id"), 64).lower()
    if not _RULE_RE.match(rule):
        raise ValueError("bad rule_id")
    path = item.get("file")
    if path not in files:
        raise ValueError("file was not part of the analysed set")
    start, end = item.get("start_line"), item.get("end_line")
    if isinstance(start, bool) or isinstance(end, bool) or not (
            isinstance(start, int) and isinstance(end, int)):
        raise ValueError("line numbers must be integers")
    lines = files[path].split("\n")
    if not 1 <= start <= end <= len(lines):
        raise ValueError("line range outside the analysed file")
    evidence = _clean(item.get("evidence"), 300)
    if not evidence or _norm(evidence) not in _norm("\n".join(lines[start - 1:end])):
        raise ValueError("evidence not found at the cited lines")
    severity = item.get("severity")
    if severity not in SEVERITIES:
        raise ValueError("bad severity")
    conf = item.get("confidence", 0.5)
    if isinstance(conf, bool) or not isinstance(conf, (int, float)):
        raise ValueError("bad confidence")
    return Issue(
        rule_id=rule if rule.startswith("llm.") else f"llm.{rule}",
        severity=severity, file=path, start_line=start, end_line=end,
        description=_clean(item.get("description"), 500),
        evidence=evidence,
        remediation=_clean(item.get("remediation"), 500),
        confidence=round(max(0.0, min(float(conf), MAX_LLM_CONFIDENCE)), 2),
        source=source)
