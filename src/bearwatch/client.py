"""BearWatch client for job monitoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

from bearwatch._internal.http_client import HttpClient
from bearwatch._internal.retry import retry_async, retry_sync
from bearwatch.config import BearWatchConfig
from bearwatch.errors import ErrorContext
from bearwatch.types import HeartbeatResponse, RequestStatus


T = TypeVar("T")


class BearWatch:
    """BearWatch client for job monitoring.

    Provides sync and async methods for heartbeat-based job monitoring.

    Example:
        ```python
        # Initialize
        bw = BearWatch(api_key="your-api-key")

        # Simple heartbeat (startedAt/completedAt auto-set to now)
        bw.ping("my-job")

        # With automatic timing (wrap)
        result = bw.wrap("my-job", lambda: do_work())

        # Manual timing control
        started_at = datetime.now(timezone.utc)
        do_work()
        bw.ping("my-job", started_at=started_at, completed_at=datetime.now(timezone.utc))

        # Async
        await bw.ping_async("my-job")
        ```
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.bearwatch.dev",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ) -> None:
        """Initialize BearWatch client.

        Args:
            api_key: API key for authentication.
            base_url: Base URL for the BearWatch API.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for retryable errors.
            retry_delay: Initial delay between retries in seconds.
        """
        self._config = BearWatchConfig(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self._http = HttpClient(self._config)

    @classmethod
    def create(cls, config: BearWatchConfig) -> BearWatch:
        """Create a BearWatch client from a config object.

        Args:
            config: BearWatch configuration.

        Returns:
            Configured BearWatch client.
        """
        return cls(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        )

    # -------------------------------------------------------------------------
    # Ping
    # -------------------------------------------------------------------------

    def ping(
        self,
        job_id: str,
        *,
        status: RequestStatus = "SUCCESS",
        output: str | None = None,
        error: str | None = None,
        started_at: datetime | str | None = None,
        completed_at: datetime | str | None = None,
        metadata: dict[str, Any] | None = None,
        retry: bool = True,
    ) -> HeartbeatResponse:
        """Send a heartbeat ping for a job (sync).

        This is the primary way to report job execution status.
        startedAt and completedAt are required by the server (auto-set to now if not provided).

        Args:
            job_id: Job identifier.
            status: Job status (default: SUCCESS).
            output: Optional output message.
            error: Optional error message (for FAILED status).
            started_at: Job start time (datetime or ISO 8601 string). Auto-set to completedAt if not provided.
            completed_at: Job completion time (datetime or ISO 8601 string). Auto-set to now if not provided.
            metadata: Optional metadata (key-value pairs).
            retry: Whether to retry on transient errors (default: True).

        Returns:
            HeartbeatResponse from the API.

        Example:
            ```python
            # Simple success (startedAt/completedAt auto-set to now)
            bw.ping("my-job")

            # With manual timing
            started_at = datetime.now(timezone.utc)
            do_work()
            bw.ping("my-job", started_at=started_at, completed_at=datetime.now(timezone.utc))

            # Report failure
            bw.ping("my-job", status="FAILED", error="Something went wrong")
            ```
        """
        context = ErrorContext(job_id=job_id, operation="ping")

        # Auto-set timestamps if not provided
        now = datetime.now(timezone.utc)
        effective_completed_at = completed_at if completed_at is not None else now
        effective_started_at = started_at if started_at is not None else effective_completed_at

        def format_datetime(dt: datetime | str) -> str:
            if isinstance(dt, datetime):
                return dt.isoformat().replace("+00:00", "Z")
            return dt

        body: dict = {
            "status": status,
            "startedAt": format_datetime(effective_started_at),
            "completedAt": format_datetime(effective_completed_at),
        }

        if output is not None:
            body["output"] = output
        if error is not None:
            body["error"] = error
        if metadata is not None:
            body["metadata"] = metadata

        def do_request() -> HeartbeatResponse:
            return self._http.post(
                f"/api/v1/ingest/jobs/{job_id}/heartbeat",
                json=body,
                context=context,
            )  # type: ignore

        if retry:
            return retry_sync(do_request, self._config)
        return do_request()

    async def ping_async(
        self,
        job_id: str,
        *,
        status: RequestStatus = "SUCCESS",
        output: str | None = None,
        error: str | None = None,
        started_at: datetime | str | None = None,
        completed_at: datetime | str | None = None,
        metadata: dict[str, Any] | None = None,
        retry: bool = True,
    ) -> HeartbeatResponse:
        """Send a heartbeat ping for a job (async).

        This is the primary way to report job execution status.
        startedAt and completedAt are required by the server (auto-set to now if not provided).

        Args:
            job_id: Job identifier.
            status: Job status (default: SUCCESS).
            output: Optional output message.
            error: Optional error message (for FAILED status).
            started_at: Job start time (datetime or ISO 8601 string). Auto-set to completedAt if not provided.
            completed_at: Job completion time (datetime or ISO 8601 string). Auto-set to now if not provided.
            metadata: Optional metadata (key-value pairs).
            retry: Whether to retry on transient errors (default: True).

        Returns:
            HeartbeatResponse from the API.
        """
        context = ErrorContext(job_id=job_id, operation="ping")

        # Auto-set timestamps if not provided
        now = datetime.now(timezone.utc)
        effective_completed_at = completed_at if completed_at is not None else now
        effective_started_at = started_at if started_at is not None else effective_completed_at

        def format_datetime(dt: datetime | str) -> str:
            if isinstance(dt, datetime):
                return dt.isoformat().replace("+00:00", "Z")
            return dt

        body: dict = {
            "status": status,
            "startedAt": format_datetime(effective_started_at),
            "completedAt": format_datetime(effective_completed_at),
        }

        if output is not None:
            body["output"] = output
        if error is not None:
            body["error"] = error
        if metadata is not None:
            body["metadata"] = metadata

        async def do_request() -> HeartbeatResponse:
            return await self._http.post_async(
                f"/api/v1/ingest/jobs/{job_id}/heartbeat",
                json=body,
                context=context,
            )  # type: ignore

        if retry:
            return await retry_async(do_request, self._config)
        return await do_request()

    # -------------------------------------------------------------------------
    # Wrap
    # -------------------------------------------------------------------------

    def wrap(
        self,
        job_id: str,
        fn: Callable[[], T],
        *,
        output: str | None = None,
        metadata: dict[str, Any] | None = None,
        retry: bool = True,
    ) -> T:
        """Wrap a function with automatic timing and heartbeat reporting (sync).

        Automatically measures execution time and reports SUCCESS or FAILED
        based on whether the function completes normally or throws an error.
        Makes a single HTTP call after execution completes.

        Args:
            job_id: Job identifier.
            fn: Function to execute.
            output: Output message to include in the heartbeat.
            metadata: Additional key-value pairs to include.
            retry: Enable/disable retry for the heartbeat request.

        Returns:
            Result of the function.

        Raises:
            Exception: Re-raises any exception from fn after reporting failure.

        Example:
            ```python
            result = bw.wrap(
                "my-job",
                lambda: do_work(),
                metadata={
                    "server": "backup-01",
                    "region": "ap-northeast-2",
                    "version": "1.2.0",
                },
            )
            ```
        """
        started_at = datetime.now(timezone.utc)
        try:
            result = fn()
            self.ping(
                job_id,
                status="SUCCESS",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                output=output,
                metadata=metadata,
                retry=retry,
            )
            return result
        except Exception as e:
            try:
                self.ping(
                    job_id,
                    status="FAILED",
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    error=str(e),
                    output=output,
                    metadata=metadata,
                    retry=retry,
                )
            except Exception:
                # Ignore errors from ping() to preserve original exception
                pass
            raise

    async def wrap_async(
        self,
        job_id: str,
        fn: Callable[[], Awaitable[T]],
        *,
        output: str | None = None,
        metadata: dict[str, Any] | None = None,
        retry: bool = True,
    ) -> T:
        """Wrap an async function with automatic timing and heartbeat reporting.

        Automatically measures execution time and reports SUCCESS or FAILED
        based on whether the function completes normally or throws an error.
        Makes a single HTTP call after execution completes.

        Args:
            job_id: Job identifier.
            fn: Async function to execute.
            output: Output message to include in the heartbeat.
            metadata: Additional key-value pairs to include.
            retry: Enable/disable retry for the heartbeat request.

        Returns:
            Result of the function.

        Raises:
            Exception: Re-raises any exception from fn after reporting failure.

        Example:
            ```python
            result = await bw.wrap_async(
                "my-job",
                async_do_work,
                metadata={
                    "server": "backup-01",
                    "region": "ap-northeast-2",
                    "version": "1.2.0",
                },
            )
            ```
        """
        started_at = datetime.now(timezone.utc)
        try:
            result = await fn()
            await self.ping_async(
                job_id,
                status="SUCCESS",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                output=output,
                metadata=metadata,
                retry=retry,
            )
            return result
        except Exception as e:
            try:
                await self.ping_async(
                    job_id,
                    status="FAILED",
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    error=str(e),
                    output=output,
                    metadata=metadata,
                    retry=retry,
                )
            except Exception:
                # Ignore errors from ping_async() to preserve original exception
                pass
            raise

    # -------------------------------------------------------------------------
    # Resource Management
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the client and release resources."""
        self._http.close()

    async def aclose(self) -> None:
        """Close the client and release resources (async)."""
        await self._http.aclose()

    def __enter__(self) -> BearWatch:
        """Enter context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager."""
        self.close()

    async def __aenter__(self) -> BearWatch:
        """Enter async context manager."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context manager."""
        await self.aclose()
