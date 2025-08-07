"""LLM service exceptions for the Geminya bot."""


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class ProviderError(LLMError):
    """Exception raised when a provider encounters an error."""

    def __init__(self, provider: str, message: str, original_error: Exception = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"Provider '{provider}' error: {message}")


class ModelNotFoundError(LLMError):
    """Exception raised when a requested model is not available."""

    def __init__(self, model: str, provider: str = None):
        self.model = model
        self.provider = provider
        if provider:
            super().__init__(f"Model '{model}' not found in provider '{provider}'")
        else:
            super().__init__(f"Model '{model}' not found in any provider")


class QuotaExceededError(LLMError):
    """Exception raised when API quota or rate limits are exceeded."""

    def __init__(self, provider: str, message: str = None):
        self.provider = provider
        message = message or "Quota or rate limit exceeded"
        super().__init__(f"Provider '{provider}': {message}")


class ConfigurationError(LLMError):
    """Exception raised when there are configuration issues."""

    pass
