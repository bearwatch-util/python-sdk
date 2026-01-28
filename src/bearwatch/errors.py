"""Error types for BearWatch SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import httpx


ErrorCode = Literal[
    "INVALID_API_KEY",
    "JOB_NOT_FOUND",
    "RATE_LIMITED",
    "SERVER_ERROR",
    "INVALID_RESPONSE",
    "NETWORK_ERROR",
    "TIMEOUT",
]


@dataclass
class ErrorContext:
    """Context information for error tracking.

    Attributes:
        job_id: The job ID involved in the operation, if any.
        run_id: The run ID involved in the operation, if any.
        operation: The operation that caused the error (ping, start, complete, fail).
    """

    job_id: str | None = None
    run_id: str | None = None
    operation: str | None = None


class BearWatchError(Exception):
    """Exception raised by BearWatch SDK operations.

    Attributes:
        code: Error code indicating the type of error.
        status_code: HTTP status code if applicable.
        response_body: Raw response body for debugging (may contain PII).
        response: The HTTP response object for retry logic (Retry-After header).
        context: Additional context about the error.
    """

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode,
        status_code: int | None = None,
        response_body: str | None = None,
        response: httpx.Response | None = None,
        context: ErrorContext | None = None,
        cause: BaseException | None = None,
    ) -> None:
        """Initialize BearWatchError.

        Args:
            message: Human-readable error message.
            code: Error code for programmatic handling.
            status_code: HTTP status code if applicable.
            response_body: Raw response body for debugging.
            response: HTTP response object for accessing headers (e.g., Retry-After).
            context: Additional context (job_id, run_id, operation).
            cause: Original exception that caused this error.
        """
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.response_body = response_body
        self.response = response
        self.context = context
        if cause:
            self.__cause__ = cause

    def __repr__(self) -> str:
        """Return detailed string representation."""
        parts = [f"BearWatchError({self.args[0]!r}, code={self.code!r}"]
        if self.status_code is not None:
            parts.append(f", status_code={self.status_code}")
        if self.context is not None:
            parts.append(f", context={self.context!r}")
        parts.append(")")
        return "".join(parts)

    @classmethod
    def network_error(
        cls,
        cause: BaseException,
        context: ErrorContext | None = None,
    ) -> BearWatchError:
        """Create a network error."""
        return cls(
            str(cause),
            code="NETWORK_ERROR",
            cause=cause,
            context=context,
        )

    @classmethod
    def timeout_error(
        cls,
        cause: BaseException,
        context: ErrorContext | None = None,
    ) -> BearWatchError:
        """Create a timeout error."""
        return cls(
            str(cause),
            code="TIMEOUT",
            cause=cause,
            context=context,
        )

    @classmethod
    def invalid_api_key(
        cls,
        response_body: str | None = None,
        context: ErrorContext | None = None,
        response: httpx.Response | None = None,
    ) -> BearWatchError:
        """Create an invalid API key error."""
        return cls(
            "Invalid API key",
            code="INVALID_API_KEY",
            status_code=401,
            response_body=response_body,
            response=response,
            context=context,
        )

    @classmethod
    def job_not_found(
        cls,
        job_id: str,
        response_body: str | None = None,
        context: ErrorContext | None = None,
        response: httpx.Response | None = None,
    ) -> BearWatchError:
        """Create a job not found error."""
        return cls(
            f"Job not found: {job_id}",
            code="JOB_NOT_FOUND",
            status_code=404,
            response_body=response_body,
            response=response,
            context=context,
        )

    @classmethod
    def rate_limited(
        cls,
        response_body: str | None = None,
        context: ErrorContext | None = None,
        response: httpx.Response | None = None,
    ) -> BearWatchError:
        """Create a rate limited error."""
        return cls(
            "Rate limited",
            code="RATE_LIMITED",
            status_code=429,
            response_body=response_body,
            response=response,
            context=context,
        )

    @classmethod
    def server_error(
        cls,
        status_code: int,
        response_body: str | None = None,
        context: ErrorContext | None = None,
        response: httpx.Response | None = None,
    ) -> BearWatchError:
        """Create a server error."""
        return cls(
            f"Server error: {status_code}",
            code="SERVER_ERROR",
            status_code=status_code,
            response_body=response_body,
            response=response,
            context=context,
        )

    @classmethod
    def invalid_response(
        cls,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        context: ErrorContext | None = None,
        response: httpx.Response | None = None,
    ) -> BearWatchError:
        """Create an invalid response error."""
        return cls(
            message,
            code="INVALID_RESPONSE",
            status_code=status_code,
            response_body=response_body,
            response=response,
            context=context,
        )
