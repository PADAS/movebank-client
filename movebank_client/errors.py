

class MBClientError(Exception):
    pass


class MBValidationError(MBClientError):
    pass


class MBForbiddenError(MBClientError):
    pass


class MBRateLimitError(MBClientError):
    """Raised when 429 rate-limit retries are exhausted. Carries the final 429
    `response` (when available) so callers can classify it as a recoverable
    rate limit rather than a hard failure."""
    pass


# ToDo: Add more custom errors as we discover them.
