"""LLM service exceptions for the Geminya bot."""

from typing import Optional


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


class RetriableError(LLMError):
    """Exception raised for server-side errors that should be retried with fallback model.

    This includes errors like:
    - HTTP 429 (Rate Limited)
    - HTTP 502 (Bad Gateway)
    - HTTP 503 (Service Unavailable)
    - HTTP 504 (Gateway Timeout)
    - Connection timeouts
    - Server overload errors
    """

    def __init__(
        self,
        provider: str,
        message: str,
        status_code: int = None,
        original_error: Exception = None,
    ):
        self.provider = provider
        self.status_code = status_code
        self.original_error = original_error

        status_info = f" (HTTP {status_code})" if status_code else ""
        super().__init__(
            f"Provider '{provider}' retriable error{status_info}: {message}"
        )

    @classmethod
    def is_retriable_error(cls, error: Exception) -> bool:
        """Check if an error should be considered retriable."""
        error_str = str(error).lower()

        # Check for specific HTTP status codes in error message
        retriable_patterns = [
            "429",  # Too Many Requests
            "502",  # Bad Gateway
            "503",  # Service Unavailable
            "504",  # Gateway Timeout
            "rate limit",
            "quota",
            "overload",
            "server error",
            "timeout",
            "connection",
            "unavailable",
            "empty response",  # Empty API responses
            "no response",
            "response body",
        ]

        return any(pattern in error_str for pattern in retriable_patterns)

    @classmethod
    def extract_status_code(cls, error: Exception) -> Optional[int]:
        """Extract HTTP status code from error if available."""
        error_str = str(error)

        # Try to extract status codes from common patterns
        import re

        # Look for patterns like "HTTP 429" or "429 Too Many Requests"
        status_match = re.search(
            r"(?:http\s+)?(\d{3})(?:\s+|$)", error_str, re.IGNORECASE
        )
        if status_match:
            return int(status_match.group(1))

        # Check if it's an OpenAI API error with status code
        if hasattr(error, "status_code"):
            return error.status_code

        return None
