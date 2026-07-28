"""Exception hierarchy for the Meet Schedule SDK.

Every API error is raised as an ``ApiException`` subclass so callers can
either catch broadly or handle specific HTTP status codes.
"""

from __future__ import annotations

from typing import Any

from meetschedule_sdk.models import ApiError


class MeetScheduleError(Exception):
    """Base exception for all SDK errors."""


# ── Client-side errors ─────────────────────────────────────────────────────


class ConfigurationError(MeetScheduleError):
    """Raised when the client is misconfigured (e.g. missing API key)."""


class NetworkError(MeetScheduleError):
    """Raised when a network-level error occurs (connection refused, timeout,
    DNS resolution failure, etc.)."""


# ── API errors (server responded with an error status) ─────────────────────


class ApiException(MeetScheduleError):
    """Base for all errors returned by the API with an HTTP error status."""

    def __init__(
        self,
        status_code: int,
        body: ApiError | None = None,
        *,
        response_text: str | None = None,
    ) -> None:
        self.status_code = status_code
        """HTTP status code."""
        self.body = body
        """Parsed error body, if available."""
        self.response_text = response_text
        """Raw response text, if the body could not be parsed."""
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.body is not None:
            return f"[{self.status_code}] {self.body.code}: {self.body.message}"
        msg = self.response_text or "no body"
        return f"[{self.status_code}] {msg}"


class UnauthorizedError(ApiException):
    """HTTP 401 — API key is missing, invalid, or revoked."""


class ForbiddenError(ApiException):
    """HTTP 403 — API key lacks the required scope."""


class NotFoundError(ApiException):
    """HTTP 404 — Resource not found or doesn't belong to this account."""


class UnprocessableEntityError(ApiException):
    """HTTP 422 — Request body validation failed."""


class TooManyRequestsError(ApiException):
    """HTTP 429 — Rate limit exceeded."""


# ── Map ────────────────────────────────────────────────────────────────────

_STATUS_CODE_TO_EXCEPTION: dict[int, type[ApiException]] = {
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    422: UnprocessableEntityError,
    429: TooManyRequestsError,
}


def map_status_code(status_code: int, **kwargs: Any) -> ApiException:
    """Return the appropriate ``ApiException`` subclass for *status_code*."""
    exc_cls = _STATUS_CODE_TO_EXCEPTION.get(status_code, ApiException)
    return exc_cls(status_code=status_code, **kwargs)
