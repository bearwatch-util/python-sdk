"""HTTP client for BearWatch SDK."""

from __future__ import annotations

from typing import Any

import httpx

from bearwatch.config import BearWatchConfig
from bearwatch.errors import BearWatchError, ErrorContext

SDK_VERSION = "0.1.0"
USER_AGENT = f"bearwatch-sdk-python/{SDK_VERSION}"


def _map_status_to_error(
    status_code: int,
    body: dict[str, Any] | None,
    raw_body: str,
    context: ErrorContext | None,
    response: httpx.Response,
) -> BearWatchError:
    """Map HTTP status code to appropriate BearWatchError.

    Args:
        status_code: HTTP status code.
        body: Parsed JSON body if available.
        raw_body: Raw response body string.
        context: Error context.
        response: HTTP response object.

    Returns:
        Appropriate BearWatchError for the status code.
    """
    if status_code == 401:
        return BearWatchError.invalid_api_key(raw_body, context, response)

    if status_code == 404:
        job_id = context.job_id if context else "unknown"
        return BearWatchError.job_not_found(job_id, raw_body, context, response)

    if status_code == 429:
        return BearWatchError.rate_limited(raw_body, context, response)

    if status_code >= 500:
        return BearWatchError.server_error(status_code, raw_body, context, response)

    # Other 4xx errors - try to extract error code from response
    if body is not None:
        error_info = body.get("error", {})
        if isinstance(error_info, dict):
            code = error_info.get("code", "INVALID_RESPONSE")
            message = error_info.get("message", f"Request failed: {status_code}")
            return BearWatchError(
                message,
                code=code,
                status_code=status_code,
                response_body=raw_body,
                response=response,
                context=context,
            )

    # 4xx with no JSON body = invalid response (matches Node.js SDK behavior)
    return BearWatchError.invalid_response(
        f"Non-JSON response for {status_code}",
        status_code=status_code,
        response_body=raw_body,
        context=context,
        response=response,
    )


def _validate_response(
    response: httpx.Response,
    context: ErrorContext | None,
) -> dict[str, Any]:
    """Validate and parse HTTP response.

    Args:
        response: HTTP response.
        context: Error context.

    Returns:
        Parsed JSON response body.

    Raises:
        BearWatchError: If response is invalid.
    """
    raw_body = response.text
    content_type = response.headers.get("content-type", "")

    # Check for error responses FIRST (before content-type validation)
    # This ensures 429/5xx errors are properly mapped even if response is not JSON
    if response.status_code >= 400:
        # Try to parse JSON body if available
        body: dict[str, Any] | None = None
        if "application/json" in content_type and raw_body:
            try:
                body = response.json()
            except Exception:
                pass  # Use None if parsing fails
        raise _map_status_to_error(response.status_code, body, raw_body, context, response)

    # Check for empty response
    if not raw_body:
        raise BearWatchError.invalid_response(
            "Empty response body",
            status_code=response.status_code,
            response_body=raw_body,
            context=context,
            response=response,
        )

    # Check content type for success responses
    if "application/json" not in content_type:
        raise BearWatchError.invalid_response(
            f"Expected application/json, got {content_type}",
            status_code=response.status_code,
            response_body=raw_body,
            context=context,
            response=response,
        )

    # Parse JSON
    try:
        body = response.json()
    except Exception as e:
        raise BearWatchError.invalid_response(
            f"Failed to parse JSON: {e}",
            status_code=response.status_code,
            response_body=raw_body,
            context=context,
            response=response,
        ) from e

    # Unwrap ApiResponse - extract data from {success, data} wrapper
    if isinstance(body, dict) and "success" in body:
        if body.get("success") is False:
            error = body.get("error", {})
            raise BearWatchError(
                message=error.get("message", "Request failed"),
                code=error.get("code", "UNKNOWN_ERROR"),
                status_code=response.status_code,
                response_body=raw_body,
                context=context,
                response=response,
            )
        return body.get("data", body)

    return body


class HttpClient:
    """HTTP client wrapper for BearWatch API."""

    def __init__(self, config: BearWatchConfig) -> None:
        """Initialize HTTP client.

        Args:
            config: BearWatch configuration.
        """
        self._config = config
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get common request headers."""
        return {
            "X-API-Key": self._config.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }

    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self._config.base_url,
                timeout=httpx.Timeout(self._config.timeout),
                headers=self._get_headers(),
            )
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self._config.base_url,
                timeout=httpx.Timeout(self._config.timeout),
                headers=self._get_headers(),
            )
        return self._async_client

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        context: ErrorContext | None = None,
    ) -> dict[str, Any]:
        """Make a synchronous POST request.

        Args:
            path: API endpoint path.
            json: JSON request body.
            context: Error context.

        Returns:
            Parsed JSON response.

        Raises:
            BearWatchError: If request fails.
        """
        client = self._get_sync_client()

        try:
            response = client.post(path, json=json)
        except httpx.TimeoutException as e:
            raise BearWatchError.timeout_error(e, context) from e
        except httpx.RequestError as e:
            raise BearWatchError.network_error(e, context) from e

        return _validate_response(response, context)

    async def post_async(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        context: ErrorContext | None = None,
    ) -> dict[str, Any]:
        """Make an asynchronous POST request.

        Args:
            path: API endpoint path.
            json: JSON request body.
            context: Error context.

        Returns:
            Parsed JSON response.

        Raises:
            BearWatchError: If request fails.
        """
        client = self._get_async_client()

        try:
            response = await client.post(path, json=json)
        except httpx.TimeoutException as e:
            raise BearWatchError.timeout_error(e, context) from e
        except httpx.RequestError as e:
            raise BearWatchError.network_error(e, context) from e

        return _validate_response(response, context)

    def close(self) -> None:
        """Close sync HTTP client."""
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None

    async def aclose(self) -> None:
        """Close async HTTP client."""
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None
