"""
BaseAgent — abstract foundation for all FUTURE VIP agents.

Provides:
  - Shared AsyncOpenAI client
  - _call_llm() with structured-output / function-calling support
  - _update_confidence() and _log_error() state helpers
  - run() abstract method (each agent implements this)
  - Retry logic with exponential backoff (tenacity)
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from openai import AsyncOpenAI, APIStatusError, APITimeoutError, RateLimitError

from app.core.config import settings
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# Default retry settings
_MAX_RETRIES = 3
_BASE_DELAY = 1.0   # seconds
_MAX_DELAY = 30.0   # seconds


class BaseAgent(ABC):
    """Abstract base class for all LangGraph agents."""

    MODEL = "gpt-4-turbo-preview"   # GPT-4.1 alias available in API
    MAX_TOKENS = 4096

    def __init__(self) -> None:
        self.name: str = self.__class__.__name__

    def _get_client(self) -> AsyncOpenAI:
        """Return an AsyncOpenAI client using the caller's key if supplied, else the system key."""
        from app.core.context import user_openai_key
        api_key = user_openai_key.get() or settings.OPENAI_API_KEY
        return AsyncOpenAI(api_key=api_key)

    # ---------------------------------------------------------------------- #
    # Abstract interface
    # ---------------------------------------------------------------------- #

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """
        Execute this agent's logic.

        Must always return a *complete* AgentState (not just changed fields).
        On any unrecoverable error, append to state["errors"] and return
        the state unchanged rather than raising.
        """

    # ---------------------------------------------------------------------- #
    # LLM call helper
    # ---------------------------------------------------------------------- #

    async def _call_llm(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
        response_format: Optional[dict] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Call the OpenAI Chat Completions API with optional function-calling.

        Parameters
        ----------
        messages       : list of {"role": ..., "content": ...} dicts
        tools          : OpenAI tool definitions (function calling schema)
        tool_choice    : "auto" | "none" | {"type":"function","function":{"name":...}}
        response_format: e.g. {"type": "json_object"} for JSON mode
        temperature    : sampling temperature
        max_tokens     : override MAX_TOKENS

        Returns
        -------
        dict with keys:
          content          — raw text content (may be None if tool called)
          tool_call_name   — name of the called tool (or None)
          tool_call_args   — parsed dict of tool arguments (or None)
          usage            — token usage dict
        """
        kwargs: dict[str, Any] = {
            "model": self.MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.MAX_TOKENS,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        if response_format:
            kwargs["response_format"] = response_format

        response = await self._retry_call(self._get_client().chat.completions.create, **kwargs)

        choice = response.choices[0]
        message = choice.message

        result: dict[str, Any] = {
            "content": message.content,
            "tool_call_name": None,
            "tool_call_args": None,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        }

        if message.tool_calls:
            tc = message.tool_calls[0]
            result["tool_call_name"] = tc.function.name
            try:
                result["tool_call_args"] = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                result["tool_call_args"] = {}

        return result

    # ---------------------------------------------------------------------- #
    # Retry helper
    # ---------------------------------------------------------------------- #

    async def _retry_call(self, func, *args, **kwargs) -> Any:
        """
        Call an async function with exponential-backoff retry.
        Retries on RateLimitError, APITimeoutError, and 5xx APIStatusErrors.
        """
        delay = _BASE_DELAY
        last_exc: Optional[Exception] = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await func(*args, **kwargs)
            except RateLimitError as exc:
                last_exc = exc
                logger.warning(
                    "[%s] Rate-limited (attempt %d/%d). Retrying in %.1fs",
                    self.name, attempt, _MAX_RETRIES, delay,
                )
            except APITimeoutError as exc:
                last_exc = exc
                logger.warning(
                    "[%s] Timeout (attempt %d/%d). Retrying in %.1fs",
                    self.name, attempt, _MAX_RETRIES, delay,
                )
            except APIStatusError as exc:
                last_exc = exc
                if exc.status_code >= 500:
                    logger.warning(
                        "[%s] Server error %s (attempt %d/%d). Retrying in %.1fs",
                        self.name, exc.status_code, attempt, _MAX_RETRIES, delay,
                    )
                else:
                    raise  # 4xx — no retry

            await asyncio.sleep(min(delay, _MAX_DELAY))
            delay *= 2

        raise last_exc  # type: ignore[misc]

    # ---------------------------------------------------------------------- #
    # State helpers
    # ---------------------------------------------------------------------- #

    def _update_confidence(self, state: AgentState, score: float) -> AgentState:
        """Record this agent's confidence score in state."""
        scores = dict(state.get("confidence_scores") or {})
        scores[self.name] = round(max(0.0, min(1.0, score)), 4)
        state["confidence_scores"] = scores
        return state

    def _log_error(self, state: AgentState, error: str) -> AgentState:
        """Append an error message to state["errors"]."""
        errors = list(state.get("errors") or [])
        errors.append(f"[{self.name}] {error}")
        state["errors"] = errors
        logger.error("[%s] %s", self.name, error)
        return state

    def _append_message(
        self,
        state: AgentState,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> AgentState:
        """Append a message to the state conversation history."""
        messages = list(state.get("messages") or [])
        entry: dict[str, Any] = {"role": role, "content": content, "agent": self.name}
        if metadata:
            entry["metadata"] = metadata
        messages.append(entry)
        state["messages"] = messages
        return state

    # ---------------------------------------------------------------------- #
    # Convenience: parse JSON from LLM content
    # ---------------------------------------------------------------------- #

    @staticmethod
    def _parse_json_content(content: Optional[str]) -> dict:
        """
        Try to extract a JSON object from LLM content string.
        Returns empty dict on failure.
        """
        if not content:
            return {}
        # Try direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        # Try to extract from markdown code fence
        match = __import__("re").search(r"```(?:json)?\s*(\{.*?\})\s*```", content, __import__("re").DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return {}
