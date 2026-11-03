"""Abstract base provider and data models for LLM backends."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional


@dataclass
class ToolCall:
    """Represents a tool or function invocation requested by the model."""
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class LLMResponse:
    """Standardized response from any LLM backend."""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Any = None
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract interface that all reasoning engines must implement."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Generate response synchronously."""
        pass

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[str]:
        """Stream generated response text tokens."""
        pass
