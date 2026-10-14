
class GeminiServiceError(Exception):
    """Base exception for Gemini analysis failures."""


class GeminiAuthenticationError(GeminiServiceError):
    """Invalid or unauthorized Gemini credentials."""


class GeminiRateLimitError(GeminiServiceError):
    """Gemini request quota or rate limit exceeded."""


class GeminiTimeoutError(GeminiServiceError):
    """Gemini request timed out."""


class GeminiUnavailableError(GeminiServiceError):
    """Gemini provider or network is unavailable."""


class GeminiInvalidResponseError(GeminiServiceError):
    """Gemini returned invalid or incomplete output."""
