"""LLM providers for goal intake and structured extraction.

Separate from the explanation-layer AIProvider so intake can use
complete_json without changing grounded explanation contracts.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import settings

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


class LLMUnavailable(RuntimeError):
    """Provider could not produce structured output. Callers fall back."""


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, *, system: str, user: str, max_tokens: int) -> LLMResult: ...

    def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> dict[str, Any]: ...


class NoProvider:
    name = "none"
    model = "none"

    def complete(self, *, system: str, user: str, max_tokens: int) -> LLMResult:
        raise LLMUnavailable("No language model is configured.")

    def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> dict[str, Any]:
        raise LLMUnavailable("No language model is configured.")


class OpenAICompatibleProvider:
    def __init__(
        self, *, name: str, api_key: str, model: str, base_url: str, timeout: float
    ) -> None:
        self.name = name
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _post(self, payload: dict[str, Any]) -> str:
        import httpx

        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMUnavailable(f"{self.name} request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMUnavailable(
                f"{self.name} returned {response.status_code}: {response.text[:200]}"
            )
        try:
            body = response.json()
            choice = body["choices"][0]
        except (ValueError, KeyError, IndexError) as exc:
            raise LLMUnavailable(f"{self.name} returned an unexpected body") from exc

        text = _strip_reasoning((choice.get("message") or {}).get("content") or "")
        if not text:
            raise LLMUnavailable(f"{self.name} returned no content.")
        return text

    def complete(self, *, system: str, user: str, max_tokens: int) -> LLMResult:
        text = self._post(
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        )
        return LLMResult(text=text, provider=self.name, model=self.model)

    def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any], max_tokens: int
    ) -> dict[str, Any]:
        instructed = (
            f"{system}\n\nReturn a single JSON object matching this schema "
            f"exactly, with no commentary:\n{json.dumps(schema)}"
        )
        text = self._post(
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": instructed},
                    {"role": "user", "content": user},
                ],
            }
        )
        try:
            parsed = json.loads(_strip_code_fence(text))
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(f"{self.name} returned unparseable JSON.") from exc
        if not isinstance(parsed, dict):
            raise LLMUnavailable(f"{self.name} returned a non-object payload.")
        return parsed


_THINK_BLOCK = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.S | re.I)
_OPEN_THINK = re.compile(r"<(think|thinking|reasoning)>.*$", re.S | re.I)


def _strip_reasoning(text: str) -> str:
    cleaned = _THINK_BLOCK.sub("", text)
    cleaned = _OPEN_THINK.sub("", cleaned)
    return cleaned.strip()


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped.split("\n", 1)[-1]
    if body.rstrip().endswith("```"):
        body = body.rstrip()[: -len("```")]
    return body.strip()


def _openai_compatible(
    *, name: str, key: str, default_base: str, default_model: str
) -> LLMProvider:
    if not key:
        return NoProvider()
    return OpenAICompatibleProvider(
        name=name,
        api_key=key,
        model=settings.ai_model.strip() or default_model,
        base_url=settings.ai_base_url.strip() or default_base,
        timeout=settings.ai_timeout_seconds,
    )


def get_llm_provider() -> LLMProvider:
    configured = (settings.ai_provider or "stub").strip().lower()
    api_key = settings.ai_api_key or os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

    if configured in {"stub", "none", "off"}:
        return NoProvider()
    if configured == "groq":
        return _openai_compatible(
            name="groq",
            key=api_key,
            default_base=GROQ_BASE_URL,
            default_model=GROQ_DEFAULT_MODEL,
        )
    if configured in {"openai", "openai-compatible"}:
        return _openai_compatible(
            name="openai",
            key=api_key,
            default_base=OPENAI_BASE_URL,
            default_model=OPENAI_DEFAULT_MODEL,
        )
    if configured != "auto" and configured not in {"openai", "groq"}:
        return NoProvider()

    if os.environ.get("GROQ_API_KEY"):
        return _openai_compatible(
            name="groq",
            key=os.environ["GROQ_API_KEY"],
            default_base=GROQ_BASE_URL,
            default_model=GROQ_DEFAULT_MODEL,
        )
    if api_key and settings.ai_base_url:
        return _openai_compatible(
            name="openai-compatible",
            key=api_key,
            default_base=settings.ai_base_url,
            default_model=settings.ai_model or GROQ_DEFAULT_MODEL,
        )
    if api_key:
        return _openai_compatible(
            name="openai",
            key=api_key,
            default_base=OPENAI_BASE_URL,
            default_model=settings.ai_model or OPENAI_DEFAULT_MODEL,
        )
    return NoProvider()
