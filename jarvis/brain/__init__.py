"""JARVIS Reasoning and Brain subsystem."""

from jarvis.brain.llm_provider import BaseLLMProvider, LLMResponse, ToolCall
from jarvis.brain.offline_provider import OfflineProvider
from jarvis.brain.gemini_provider import GeminiProvider
from jarvis.brain.openai_provider import OpenAIProvider
from jarvis.brain.router import ActionRouter, action_router
from jarvis.brain.prompt_templates import build_system_prompt, JARVIS_SYSTEM_PERSONA

__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "ToolCall",
    "OfflineProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "ActionRouter",
    "action_router",
    "build_system_prompt",
    "JARVIS_SYSTEM_PERSONA",
]
