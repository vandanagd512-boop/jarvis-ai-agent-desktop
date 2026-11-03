"""Domain exceptions for JARVIS."""

class JarvisError(Exception):
    """Base exception for all JARVIS errors."""
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(JarvisError):
    """Raised when configuration validation or environment loading fails."""


class BrainError(JarvisError):
    """Raised when the reasoning engine or LLM encounters an error."""


class LLMQuotaExceededError(BrainError):
    """Raised when LLM API quota or rate limit is exceeded."""


class VoiceError(JarvisError):
    """Raised when speech synthesis or recognition fails."""


class AutomationError(JarvisError):
    """Raised when Windows system automation or UI automation fails."""


class SecurityError(JarvisError):
    """Raised when an operation violates security policy or sandbox rules."""


class PluginError(JarvisError):
    """Raised when plugin loading, execution, or unloading fails."""


class MemoryError(JarvisError):
    """Raised when memory persistence or database operations fail."""


class WorkflowError(JarvisError):
    """Raised when workflow orchestration or step execution fails."""
