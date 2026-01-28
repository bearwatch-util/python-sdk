"""Retry logic for BearWatch SDK."""

from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Awaitable, Callable, TypeVar

from bearwatch.errors import BearWatchError

if TYPE_CHECKING:
    from bearwatch.config import BearWatchConfig


T = TypeVar("T")

# Status codes that should be retried
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Error codes that should be retried
RETRYABLE_ERROR_CODES = {"NETWORK_ERROR", "TIMEOUT", "RATE_LIMITED", "SERVER_ERROR"}


def is_retryable_status(status_code: int) -> bool:
    """Check if a status code should be retried."""
    return status_code in RETRYABLE_STATUS_CODES


def is_retryable_error(error: BearWatchError) -> bool:
    """Check if an error should be retried.

    If status_code is present, use it exclusively to determine retryability.
    This prevents 4xx client errors from being retried even if error.code
    happens to be a retryable code (e.g., SERVER_ERROR for unknown 4xx).

    If status_code is absent (network errors, timeouts), fall back to error.code.
    """
    if error.status_code is not None:
        return error.status_code in RETRYABLE_STATUS_CODES
    return error.code in RETRYABLE_ERROR_CODES


def parse_retry_after(value: str) -> float | None:
    """Parse Retry-After header value.

    Supports both seconds (integer/float) and HTTP-date formats.

    Args:
        value: Retry-After header value.

    Returns:
        Delay in seconds, or None if parsing fails.
    """
    # Try parsing as seconds (integer or float)
    try:
        return float(value)
    except ValueError:
        pass

    # Try parsing as HTTP-date (RFC 7231)
    try:
        date = parsedate_to_datetime(value)
        delay = (date - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, delay)
    except (ValueError, TypeError):
        pass

    return None


def calculate_delay(
    attempt: int,
    base_delay: float,
    error: BearWatchError | None = None,
) -> float:
    """Calculate delay before next retry attempt.

    Uses Retry-After header if present for 429 responses,
    otherwise uses exponential backoff with jitter.

    Args:
        attempt: Current attempt number (0-indexed).
        base_delay: Base delay in seconds.
        error: BearWatchError with response for Retry-After header.

    Returns:
        Delay in seconds before next retry.
    """
    # Check for Retry-After header on 429 responses
    if error is not None and error.response is not None:
        if error.response.status_code == 429:
            retry_after = error.response.headers.get("Retry-After")
            if retry_after:
                parsed = parse_retry_after(retry_after)
                if parsed is not None:
                    return parsed

    # Exponential backoff with jitter: base * 2^attempt * (0.5 to 1.0)
    delay = base_delay * (2**attempt)
    jitter = random.uniform(0.5, 1.0)
    return delay * jitter


def retry_sync(
    fn: Callable[[], T],
    config: BearWatchConfig,
) -> T:
    """Execute a function with retry logic (sync).

    Args:
        fn: Function to execute.
        config: BearWatch configuration.

    Returns:
        Result of the function.

    Raises:
        BearWatchError: If all retry attempts fail.
    """
    last_error: BearWatchError | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return fn()
        except BearWatchError as e:
            last_error = e

            # Don't retry if not retryable or this was the last attempt
            if not is_retryable_error(e) or attempt >= config.max_retries:
                raise

            # Calculate delay and sleep (error contains response for Retry-After)
            delay = calculate_delay(attempt, config.retry_delay, e)
            time.sleep(delay)

    # Should not reach here, but satisfy type checker
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state in retry loop")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    config: BearWatchConfig,
) -> T:
    """Execute an async function with retry logic.

    Args:
        fn: Async function to execute.
        config: BearWatch configuration.

    Returns:
        Result of the function.

    Raises:
        BearWatchError: If all retry attempts fail.
    """
    last_error: BearWatchError | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await fn()
        except BearWatchError as e:
            last_error = e

            # Don't retry if not retryable or this was the last attempt
            if not is_retryable_error(e) or attempt >= config.max_retries:
                raise

            # Calculate delay and sleep (error contains response for Retry-After)
            delay = calculate_delay(attempt, config.retry_delay, e)
            await asyncio.sleep(delay)

    # Should not reach here, but satisfy type checker
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state in retry loop")
