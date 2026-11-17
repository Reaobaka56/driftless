import json

import pytest

from driftless.llm import errors as E
from driftless.llm.chain import LLMPolicy, analyze_with_fallback
from driftless.llm.providers import AnthropicProvider, OpenAICompatProvider, providers_from_env
from driftless.llm.validate import validate_findings

FILES = {"a.ts": "const x = 1;\neval(userInput);\nconsole.log(x);"}


def good(**over):
    f = {"rule_id": "unsafe-eval", "severity": "high", "file": "a.ts", "start_line": 2,
         "end_line": 2, "description": "eval on user input", "evidence": "eval(userInput);",
         "remediation": "avoid eval", "confidence": 0.9}
    f.update(over)
    return json.dumps({"findings": [f]})


class Fake:
    def __init__(self, name, script, configured=True):
        self.name, self.script, self._c, self.calls = name, list(script), configured, 0

    @property
    def configured(self):
        return self._c

    def complete(self, system, user, *, timeout):
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


class Clock:
    def __init__(self):
        self.t, self.sleeps = 0.0, []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def run(providers, policy=LLMPolicy()):
    c = Clock()
    out = analyze_with_fallback(providers, "sys", "user", FILES, policy=policy,
                                clock=c, sleep=c.sleep)
    return out, c


def test_primary_succeeds():
    p, s = Fake("primary", [good()]), Fake("secondary", [good()])
    out, _ = run([p, s])
    assert out.status == "llm" and out.provider == "primary" and s.calls == 0
    assert out.issues[0].source == "llm:primary" and out.issues[0].rule_id == "llm.unsafe-eval"


def test_primary_unconfigured_skipped_then_secondary():
    out, _ = run([Fake("primary", [], configured=False), Fake("secondary", [good()])])
    assert [a.outcome for a in out.attempts] == ["unconfigured", "ok"]
    assert out.provider == "secondary"


def test_primary_unavailable_falls_to_secondary():
    p = Fake("primary", [E.Unavailable("down"), E.Unavailable("down")])
    out, _ = run([p, Fake("secondary", [good()])])
    assert p.calls == 2 and out.provider == "secondary"


def test_rate_limit_waits_retry_after_then_succeeds():
    p = Fake("primary", [E.RateLimited(retry_after=3), good()])
    out, c = run([p])
    assert out.provider == "primary" and c.sleeps == [3]
    assert [a.outcome for a in out.attempts] == ["rate_limited", "ok"]


def test_rate_limit_retry_after_is_capped():
    p = Fake("primary", [E.RateLimited(retry_after=9999), good()])
    _, c = run([p], LLMPolicy(max_retry_after=5, overall_deadline=100))
    assert c.sleeps == [5]


def test_timeout_bounded_retries_then_fallback():
    p = Fake("primary", [E.Timeout(), E.Timeout(), E.Timeout()])
    out, _ = run([p, Fake("secondary", [good()])])
    assert p.calls == 2  # max_attempts, never infinite
    assert out.provider == "secondary"


def test_invalid_output_retried_once_then_fallback():
    p = Fake("primary", ["this is not json", "still { not json"])
    out, _ = run([p, Fake("secondary", [good()])])
    assert [a.outcome for a in out.attempts][:2] == ["invalid_output", "invalid_output"]
    assert out.provider == "secondary"


def test_auth_error_not_retried():
    p = Fake("primary", [E.AuthError("401")])
    out, _ = run([p])
    assert p.calls == 1 and out.attempts[0].outcome == "auth_error"


def test_all_providers_unavailable_reports_it_without_raising():
    out, _ = run([Fake("a", [E.Unavailable(), E.Unavailable()]),
                  Fake("b", [E.AuthError()]), Fake("c", [], configured=False)])
    assert out.status == "unavailable" and out.issues == [] and out.provider is None
    assert len(out.attempts) == 4


def test_unexpected_provider_exception_is_contained():
    out, _ = run([Fake("a", [RuntimeError("bug")]), Fake("b", [good()])])
    assert out.provider == "b"


def test_overall_deadline_stops_everything():
    c = Clock()

    class Slow(Fake):
        def complete(self, system, user, *, timeout):
            c.t += 100  # the call itself eats the whole budget
            return super().complete(system, user, timeout=timeout)

    p, s = Slow("a", [E.Timeout()]), Fake("b", [good()])
    out = analyze_with_fallback([p, s], "s", "u", FILES, policy=LLMPolicy(overall_deadline=50),
                                clock=c, sleep=c.sleep)
    assert s.calls == 0 and out.status == "unavailable"
    assert out.attempts[-1].outcome == "deadline"


def test_unaffordable_retry_is_skipped_but_next_provider_still_runs():
    p, s = Fake("a", [E.Timeout(), good()]), Fake("b", [good()])
    out, c = run([p, s], LLMPolicy(overall_deadline=0.5, backoff_base=1.0))
    assert p.calls == 1 and c.sleeps == [] and out.provider == "b"


def test_no_files_skips_analysis():
    out = analyze_with_fallback([Fake("a", [])], "s", "u", {})
    assert out.status == "skipped"


# ---- validation: model output is untrusted data ----
@pytest.mark.parametrize("bad", [
    {"file": "other.ts"},                      # not in analysed set
    {"start_line": 99, "end_line": 99},        # outside file
    {"evidence": "fetch(attackerUrl)"},         # not at cited lines (hallucinated)
    {"severity": "apocalyptic"},
    {"rule_id": "Bad Rule!"},
    {"start_line": "2"},
])
def test_ungrounded_or_malformed_findings_rejected(bad):
    with pytest.raises(E.InvalidOutput):
        validate_findings(good(**bad), FILES, "llm:x")


def test_partial_rejection_keeps_valid_findings():
    raw = json.dumps({"findings": [json.loads(good())["findings"][0],
                                   {"rule_id": "x", "file": "nope.ts"}]})
    v = validate_findings(raw, FILES, "llm:x")
    assert len(v.issues) == 1 and len(v.rejected) == 1


def test_confidence_capped_and_text_sanitised():
    v = validate_findings(good(confidence=1.0, remediation="run\x00 this\x1b"), FILES, "llm:x")
    assert v.issues[0].confidence == 0.8 and "\x00" not in v.issues[0].remediation


def test_json_in_code_fence_and_empty_findings():
    assert validate_findings("```json\n" + good() + "\n```", FILES, "llm:x").issues
    assert validate_findings('{"findings": []}', FILES, "llm:x").issues == []


# ---- HTTP provider mapping ----
def transport(status, body=b"{}", headers=None):
    return lambda url, h, b, t: (status, headers or {}, body)


@pytest.mark.parametrize("status,exc", [(401, E.AuthError), (403, E.AuthError), (429, E.RateLimited),
                                        (500, E.Unavailable), (408, E.Timeout), (400, E.ProviderError)])
def test_http_status_mapping(status, exc):
    p = AnthropicProvider("k", transport=transport(status, headers={"retry-after": "7"}))
    with pytest.raises(exc) as ei:
        p.complete("s", "u", timeout=1)
    if status == 429:
        assert ei.value.retry_after == 7.0


def test_anthropic_and_openai_parse_success_and_bad_shapes():
    a = AnthropicProvider("k", transport=transport(200, json.dumps(
        {"content": [{"type": "text", "text": "hi"}]}).encode()))
    assert a.complete("s", "u", timeout=1) == "hi"
    o = OpenAICompatProvider("k", "m", transport=transport(200, json.dumps(
        {"choices": [{"message": {"content": "yo"}}]}).encode()))
    assert o.complete("s", "u", timeout=1) == "yo"
    with pytest.raises(E.InvalidOutput):
        AnthropicProvider("k", transport=transport(200, b"{}")).complete("s", "u", timeout=1)
    with pytest.raises(E.InvalidOutput):
        OpenAICompatProvider("k", "m", transport=transport(200, b"not json")).complete("s", "u", timeout=1)


def test_provider_env_configuration_and_priority():
    assert not any(p.configured for p in providers_from_env({}))
    ps = providers_from_env({"OPENAI_API_KEY": "k", "DRIFTLESS_OPENAI_MODEL": "m",
                             "ANTHROPIC_API_KEY": "k2", "DRIFTLESS_LLM_PRIMARY": "openai"})
    assert [p.name for p in ps] == ["openai-compatible", "anthropic"] and all(p.configured for p in ps)
    assert not providers_from_env({"OPENAI_API_KEY": "k"})[1].configured  # model required
