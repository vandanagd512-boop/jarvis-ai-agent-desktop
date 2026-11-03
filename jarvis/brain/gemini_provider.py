"""Google Gemini LLM provider using the modern google-genai SDK."""

from __future__ import annotations
import os
from typing import Any, Dict, Iterator, List, Optional
from jarvis.brain.llm_provider import BaseLLMProvider, LLMResponse, ToolCall
from jarvis.core.config import get_settings
from jarvis.core.exceptions import BrainError, LLMQuotaExceededError
from jarvis.core.logger import get_logger

logger = get_logger("JARVIS.GeminiBrain")


class GeminiProvider(BaseLLMProvider):
    """Reasoning provider powered by Google Gemini models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client = None

        if self.api_key:
            self._init_client()
        else:
            logger.warning("No GEMINI_API_KEY provided. GeminiProvider will operate in inactive mode.")

    def _init_client(self) -> None:
        """Initialize Google GenAI client."""
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            logger.info(f"Initialized Gemini client with model '{self.model_name}'")
        except Exception as exc:
            logger.error(f"Failed to initialize google-genai client: {exc}")
            self._client = None

    def is_available(self) -> bool:
        """Check if API key and client are configured."""
        return bool(self.api_key and self._client is not None)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Generate response and parse function calls."""
        if not self.is_available():
            raise BrainError("Gemini client is not initialized or API key is missing.")

        try:
            from google.genai import types

            contents: List[Any] = []

            # Format multi-turn conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append(
                        types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=msg["content"])],
                        )
                    )

            # Append current prompt
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                )
            )

            config = types.GenerateContentConfig(
                system_instruction=system_prompt or "You are JARVIS, an elite Windows desktop assistant.",
                temperature=0.3,
            )

            candidate_models = [self.model_name, "gemini-flash-lite-latest", "gemini-3.8-flash"]
            # Remove duplicates preserving order
            seen = set()
            models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

            response = None
            last_err = None
            for m in models_to_try:
                try:
                    response = self._client.models.generate_content(
                        model=m,
                        contents=contents,
                        config=config,
                    )
                    break
                except Exception as exc:
                    last_err = exc
                    if "503" in str(exc) or "404" in str(exc) or "UNAVAILABLE" in str(exc):
                        logger.warning(f"Gemini model '{m}' busy or unavailable ({exc}). Trying next candidate...")
                        continue
                    raise

            if response is None:
                raise last_err or BrainError("All candidate Gemini models failed.")

            tool_calls: List[ToolCall] = []
            content_text = ""

            if hasattr(response, "function_calls") and response.function_calls:
                for fc in response.function_calls:
                    args = dict(fc.args) if hasattr(fc, "args") and fc.args else {}
                    tool_calls.append(ToolCall(name=fc.name, arguments=args))

            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if not tool_calls and hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args = dict(fc.args) if fc.args else {}
                        tool_calls.append(ToolCall(name=fc.name, arguments=args))
                    elif hasattr(part, "text") and part.text:
                        content_text += part.text

            return LLMResponse(
                content=content_text or (getattr(response, "text", "") or ""),
                tool_calls=tool_calls,
                raw_response=response,
            )

        except Exception as exc:
            err_msg = str(exc)
            if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg or "quota" in err_msg.lower():
                raise LLMQuotaExceededError(f"Gemini API quota exceeded: {err_msg}")
            logger.error(f"Error during Gemini generation: {exc}")
            raise BrainError(f"Gemini generation error: {exc}")

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[str]:
        """Stream response chunks from Gemini."""
        if not self.is_available():
            raise BrainError("Gemini client is not initialized.")

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=system_prompt or "You are JARVIS, an elite Windows desktop assistant.",
                temperature=0.3,
            )
            for chunk in self._client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            logger.error(f"Error during Gemini streaming: {exc}")
            raise BrainError(f"Gemini streaming error: {exc}")
