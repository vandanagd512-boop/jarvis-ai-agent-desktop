"""OpenAI and local OpenAI-compatible LLM provider."""

from __future__ import annotations
import json
import os
from typing import Any, Dict, Iterator, List, Optional
from jarvis.brain.llm_provider import BaseLLMProvider, LLMResponse, ToolCall
from jarvis.core.config import get_settings
from jarvis.core.exceptions import BrainError, LLMQuotaExceededError
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.OpenAIBrain")


class OpenAIProvider(BaseLLMProvider):
    """Reasoning provider supporting OpenAI and local LLM endpoints (Ollama / LM Studio)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        self.model_name = model_name or settings.OPENAI_MODEL
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self._client = None
        self._quota_exhausted = False

        if self.api_key:
            self._init_client()
        else:
            logger.info("OpenAI API key not set; OpenAIProvider initialized in inactive mode.")

    def _init_client(self) -> None:
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"Initialized OpenAI client with model '{self.model_name}'")
        except Exception as exc:
            logger.error(f"Failed to initialize OpenAI client: {exc}")
            self._client = None

    def is_available(self) -> bool:
        return bool(self.api_key and self._client is not None and not self._quota_exhausted)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        if not self.is_available():
            raise BrainError("OpenAI client is not initialized or API key is missing.")

        try:
            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            if conversation_history:
                for msg in conversation_history:
                    role = "assistant" if msg["role"] == "assistant" else "user"
                    messages.append({"role": role, "content": msg["content"]})

            messages.append({"role": "user", "content": prompt})

            kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.3,
            }
            if tools:
                kwargs["tools"] = tools

            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content or ""

            tool_calls: List[ToolCall] = []
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except Exception:
                        args = {}
                    tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                raw_response=response,
                finish_reason=choice.finish_reason,
            )
        except Exception as exc:
            err_msg = str(exc)
            if "insufficient_quota" in err_msg or "rate_limit" in err_msg or "429" in err_msg or "credit_balance_exhausted" in err_msg:
                self._quota_exhausted = True
                logger.warning("OpenAI credit quota exhausted. Marking OpenAIProvider inactive.")
                raise LLMQuotaExceededError(f"OpenAI quota exceeded: {err_msg}")
            logger.error(f"Error during OpenAI generation: {exc}")
            raise BrainError(f"OpenAI error: {exc}")

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[str]:
        if not self.is_available():
            raise BrainError("OpenAI client is not initialized.")

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = self._client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
