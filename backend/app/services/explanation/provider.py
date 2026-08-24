"""Replaceable AI providers. Never persist keys. Stub is the default."""

from __future__ import annotations

import json
import re
from typing import Protocol

import httpx

from app.core.config import settings
from app.services.explanation.prompts import SYSTEM_PROMPT, user_prompt
from app.services.explanation.schema import AIContext, GroundedAnswer


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AIProvider(Protocol):
    def generate_explanation(self, context: AIContext, query: str | None) -> GroundedAnswer: ...

    def answer_grounded_query(self, context: AIContext, query: str) -> GroundedAnswer: ...


class StubProvider:
    """No network. Forces deterministic fallback."""

    def generate_explanation(self, context: AIContext, query: str | None) -> GroundedAnswer:
        raise ProviderError("unavailable", "AI provider is not configured")

    def answer_grounded_query(self, context: AIContext, query: str) -> GroundedAnswer:
        raise ProviderError("unavailable", "AI provider is not configured")


class OpenAICompatibleProvider:
    def generate_explanation(self, context: AIContext, query: str | None) -> GroundedAnswer:
        return self._complete(context, query)

    def answer_grounded_query(self, context: AIContext, query: str) -> GroundedAnswer:
        return self._complete(context, query)

    def _complete(self, context: AIContext, query: str | None) -> GroundedAnswer:
        if not settings.ai_api_key:
            raise ProviderError("unavailable", "AI provider is not configured")
        payload = {
            "model": settings.ai_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt(context, query)},
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        url = settings.ai_base_url.rstrip("/") + "/chat/completions"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=settings.ai_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ProviderError("timeout", "AI provider timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("unavailable", "AI provider is unavailable") from exc
        if response.status_code >= 400:
            raise ProviderError("unavailable", f"AI provider returned {response.status_code}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderError("malformed", "AI provider returned unexpected payload") from exc
        return parse_model_json(content)


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_model_json(content: str) -> GroundedAnswer:
    text = content.strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError("malformed", "AI provider returned non-JSON") from exc
    try:
        return GroundedAnswer.model_validate({**data, "source": "llm"})
    except Exception as exc:
        raise ProviderError("malformed", "AI provider JSON failed schema validation") from exc


def get_provider() -> AIProvider:
    if settings.ai_provider == "openai" and settings.ai_api_key:
        return OpenAICompatibleProvider()
    return StubProvider()
