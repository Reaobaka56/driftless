"""Ordered provider fallback with bounded retries. Never raises for provider failures."""
from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from driftless.issues import Issue
from driftless.llm.errors import (
    AuthError,
    InvalidOutput,
    ProviderError,
    RateLimited,
    Timeout,
    Unavailable,
)
from driftless.llm.providers import LLMProvider
from driftless.llm.validate import validate_findings


@dataclass(frozen=True)
class LLMPolicy:
    per_call_timeout: float = 30.0
    max_attempts: int = 2          # per provider
    overall_deadline: float = 90.0  # across all providers
    max_retry_after: float = 20.0
    backoff_base: float = 1.0


@dataclass
class Attempt:
    provider: str
    # ok, unconfigured, auth_error, rate_limited, timeout, unavailable, invalid_output, error, deadline
    outcome: str
    detail: str = ""
    duration_s: float = 0.0


@dataclass
class AnalysisOutcome:
    status: str  # "llm" | "unavailable" | "skipped"
    provider: str | None = None
    issues: list[Issue] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"status": self.status, "provider": self.provider,
                "rejected": self.rejected,
                "attempts": [a.__dict__ for a in self.attempts]}


def analyze_with_fallback(
    providers: Sequence[LLMProvider], system: str, user: str, files: dict[str, str],
    *, policy: LLMPolicy = LLMPolicy(),
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> AnalysisOutcome:
    out = AnalysisOutcome(status="unavailable")
    if not files:
        out.status = "skipped"
        return out
    start = clock()

    for p in providers:
        if not p.configured:
            out.attempts.append(Attempt(p.name, "unconfigured"))
            continue
        for n in range(policy.max_attempts):
            remaining = policy.overall_deadline - (clock() - start)
            if remaining <= 0:
                out.attempts.append(Attempt(p.name, "deadline", "overall deadline reached"))
                return out
            t0 = clock()
            outcome, detail, wait = "error", "", 0.0
            try:
                raw = p.complete(system, user, timeout=min(policy.per_call_timeout, remaining))
                v = validate_findings(raw, files, source=f"llm:{p.name}")
                out.attempts.append(Attempt(p.name, "ok", duration_s=clock() - t0))
                out.status, out.provider = "llm", p.name
                out.issues, out.rejected = v.issues, v.rejected
                return out
            except AuthError as e:
                outcome, detail = "auth_error", str(e)
                retry = False
            except RateLimited as e:
                outcome, detail, retry = "rate_limited", str(e), True
                wait = min(e.retry_after if e.retry_after is not None else policy.backoff_base * 2 ** n,
                           policy.max_retry_after)
            except (Timeout, Unavailable, InvalidOutput) as e:
                outcome = {Timeout: "timeout", Unavailable: "unavailable",
                           InvalidOutput: "invalid_output"}[type(e)]
                detail, retry = str(e), True
                wait = policy.backoff_base * 2 ** n
            except ProviderError as e:
                outcome, detail, retry = "error", str(e), False
            except Exception as e:  # noqa: BLE001 - a provider bug must not fail the scan
                outcome, detail, retry = "error", f"{type(e).__name__}: {e}", False
            out.attempts.append(Attempt(p.name, outcome, detail[:200], clock() - t0))
            last = n == policy.max_attempts - 1
            if not retry or last:
                break
            if (clock() - start) + wait >= policy.overall_deadline:
                out.attempts.append(Attempt(p.name, "deadline", "no time left to retry"))
                break
            sleep(wait)
    return out
