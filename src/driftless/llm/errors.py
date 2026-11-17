class ProviderError(Exception):
    """Base class. Generic provider errors are NOT retried."""


class Unavailable(ProviderError):
    """Provider unreachable or returned 5xx (transient)."""


class AuthError(ProviderError):
    """Bad or missing credentials. Never retried."""


class RateLimited(ProviderError):
    def __init__(self, message: str = "rate limited", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class Timeout(ProviderError):
    pass


class InvalidOutput(ProviderError):
    """Model output was not valid or not grounded in the scanned files."""
