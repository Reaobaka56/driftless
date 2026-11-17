"""LLM providers over plain HTTPS (stdlib only; no vendor SDK dependency)."""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Protocol

from driftless.llm.errors import (
    AuthError,
    InvalidOutput,
    ProviderError,
    RateLimited,
    Timeout,
    Unavailable,
)

# (url, headers, body, timeout) -> (status, lowercase-headers, body)
Transport = Callable[[str, dict, bytes, float], tuple[int, dict, bytes]]


class LLMProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def complete(self, system: str, user: str, *, timeout: float) -> str: ...


def urllib_transport(url: str, headers: dict, body: bytes, timeout: float):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read(2_000_000)
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read(100_000)
    except TimeoutError as e:
        raise Timeout(str(e) or "timed out") from e
    except urllib.error.URLError as e:
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            raise Timeout("timed out") from e
        raise Unavailable(f"connection failed: {e.reason}") from e


def _check_status(status: int, headers: Mapping[str, str]) -> None:
    if status < 400:
        return
    if status in (401, 403):
        raise AuthError(f"HTTP {status}")
    if status == 429:
        try:
            ra = float(headers.get("retry-after", ""))
        except ValueError:
            ra = None
        raise RateLimited("HTTP 429", retry_after=ra)
    if status == 408:
        raise Timeout("HTTP 408")
    if status >= 500:
        raise Unavailable(f"HTTP {status}")
    raise ProviderError(f"HTTP {status}")


def _json(body: bytes):
    try:
        return json.loads(body)
    except ValueError as e:
        raise InvalidOutput("response body is not JSON") from e


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str = "claude-sonnet-5-5",
                 base_url: str = "https://api.anthropic.com",
                 transport: Transport = urllib_transport):
        self._key, self.model, self._base, self._t = api_key, model, base_url, transport

    @property
    def configured(self) -> bool:
        return bool(self._key)

    def complete(self, system: str, user: str, *, timeout: float) -> str:
        body = json.dumps({"model": self.model, "max_tokens": 4096, "system": system,
                           "messages": [{"role": "user", "content": user}]}).encode()
        headers = {"content-type": "application/json", "x-api-key": self._key or "",
                   "anthropic-version": "2023-06-01"}
        status, rh, raw = self._t(f"{self._base}/v1/messages", headers, body, timeout)
        _check_status(status, rh)
        try:
            blocks = _json(raw)["content"]
            return "".join(b["text"] for b in blocks if b.get("type") == "text")
        except (KeyError, TypeError) as e:
            raise InvalidOutput("unexpected Anthropic response shape") from e


class OpenAICompatProvider:
    name = "openai-compatible"

    def __init__(self, api_key: str | None, model: str | None,
                 base_url: str = "https://api.openai.com/v1",
                 transport: Transport = urllib_transport):
        self._key, self.model, self._base, self._t = api_key, model, base_url, transport

    @property
    def configured(self) -> bool:
        return bool(self._key and self.model)

    def complete(self, system: str, user: str, *, timeout: float) -> str:
        body = json.dumps({"model": self.model, "max_tokens": 4096, "messages": [
            {"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        headers = {"content-type": "application/json", "authorization": f"Bearer {self._key}"}
        status, rh, raw = self._t(f"{self._base}/chat/completions", headers, body, timeout)
        _check_status(status, rh)
        try:
            text = _json(raw)["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise InvalidOutput("unexpected chat-completions response shape") from e
        if not isinstance(text, str):
            raise InvalidOutput("empty completion")
        return text


def providers_from_env(env: Mapping[str, str]) -> list[LLMProvider]:
    """Priority order: DRIFTLESS_LLM_PRIMARY ('anthropic' default | 'openai') first."""
    anthropic = AnthropicProvider(
        env.get("ANTHROPIC_API_KEY"), env.get("DRIFTLESS_ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    openai = OpenAICompatProvider(
        env.get("OPENAI_API_KEY"), env.get("DRIFTLESS_OPENAI_MODEL"),
        env.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    return [openai, anthropic] if env.get("DRIFTLESS_LLM_PRIMARY") == "openai" else [anthropic, openai]
