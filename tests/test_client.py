"""Tests for BearWatch client."""

import json
from datetime import datetime, timezone

import pytest
import respx
from httpx import Response

from bearwatch import BearWatch, BearWatchError


@pytest.fixture
def bw() -> BearWatch:
    """Create a BearWatch client for testing."""
    return BearWatch(api_key="test-api-key", base_url="https://api.test.com")


def _api_response(data: dict) -> dict:
    """Wrap data in ApiResponse format."""
    return {"success": True, "data": data}


def _heartbeat_data(
    job_id: str = "my-job",
    run_id: str = "run-123",
    status: str = "SUCCESS",
) -> dict:
    """Create heartbeat response data."""
    return {
        "runId": run_id,
        "jobId": job_id,
        "status": status,
        "receivedAt": "2024-01-01T00:00:00Z",
    }


class TestBearWatchClient:
    """Tests for BearWatch client initialization."""

    def test_init_with_defaults(self) -> None:
        """Test client initialization with defaults."""
        bw = BearWatch(api_key="test-key")
        assert bw._config.api_key == "test-key"
        assert bw._config.base_url == "https://api.bearwatch.dev"
        assert bw._config.timeout == 30.0

    def test_init_with_custom_values(self) -> None:
        """Test client initialization with custom values."""
        bw = BearWatch(
            api_key="test-key",
            base_url="https://custom.api.com",
            timeout=60.0,
            max_retries=5,
            retry_delay=1.0,
        )
        assert bw._config.base_url == "https://custom.api.com"
        assert bw._config.timeout == 60.0
        assert bw._config.max_retries == 5
        assert bw._config.retry_delay == 1.0


class TestPing:
    """Tests for ping method."""

    @respx.mock
    def test_ping_success(self, bw: BearWatch) -> None:
        """Test successful ping."""
        respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        response = bw.ping("my-job")

        # SDK unwraps ApiResponse, returns data directly
        assert response["jobId"] == "my-job"
        assert response["status"] == "SUCCESS"
        assert response["receivedAt"] == "2024-01-01T00:00:00Z"

    @respx.mock
    def test_ping_with_output(self, bw: BearWatch) -> None:
        """Test ping with output."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        bw.ping("my-job", output="Job completed successfully")

        # Verify request body contains status and output
        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "SUCCESS"
        assert body["output"] == "Job completed successfully"

    @respx.mock
    def test_ping_auto_sets_timestamps(self, bw: BearWatch) -> None:
        """Test ping auto-sets startedAt and completedAt when not provided."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        bw.ping("my-job")

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "SUCCESS"
        assert "startedAt" in body
        assert "completedAt" in body
        # When neither provided, startedAt equals completedAt
        assert body["startedAt"] == body["completedAt"]

    @respx.mock
    def test_ping_with_error(self, bw: BearWatch) -> None:
        """Test ping with error message."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data(status="FAILED")))
        )

        bw.ping("my-job", status="FAILED", error="Something went wrong")

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "FAILED"
        assert body["error"] == "Something went wrong"

    @respx.mock
    def test_ping_with_timestamps(self, bw: BearWatch) -> None:
        """Test ping with started_at and completed_at."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        started = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2024, 1, 1, 10, 0, 5, tzinfo=timezone.utc)
        bw.ping("my-job", started_at=started, completed_at=completed)

        body = json.loads(route.calls[0].request.content)
        assert body["startedAt"] == "2024-01-01T10:00:00Z"
        assert body["completedAt"] == "2024-01-01T10:00:05Z"

    @respx.mock
    def test_ping_job_not_found(self, bw: BearWatch) -> None:
        """Test ping with non-existent job."""
        respx.post("https://api.test.com/api/v1/ingest/jobs/unknown-job/heartbeat").mock(
            return_value=Response(
                404,
                json={
                    "success": False,
                    "error": {
                        "code": "JOB_NOT_FOUND",
                        "message": "Job not found",
                    },
                },
            )
        )

        with pytest.raises(BearWatchError) as exc_info:
            bw.ping("unknown-job", retry=False)

        assert exc_info.value.code == "JOB_NOT_FOUND"
        assert exc_info.value.status_code == 404

    @respx.mock
    def test_ping_invalid_api_key(self, bw: BearWatch) -> None:
        """Test ping with invalid API key."""
        respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(
                401,
                json={
                    "success": False,
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "Invalid API key",
                    },
                },
            )
        )

        with pytest.raises(BearWatchError) as exc_info:
            bw.ping("my-job", retry=False)

        assert exc_info.value.code == "INVALID_API_KEY"
        assert exc_info.value.status_code == 401


class TestWrap:
    """Tests for wrap method."""

    @respx.mock
    def test_wrap_success(self, bw: BearWatch) -> None:
        """Test successful wrap with single HTTP call."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        result = bw.wrap("my-job", lambda: "result")

        assert result == "result"
        # Only ONE HTTP call (no start, just completion)
        assert len(route.calls) == 1

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "SUCCESS"
        assert "startedAt" in body
        assert "completedAt" in body

    @respx.mock
    def test_wrap_failure(self, bw: BearWatch) -> None:
        """Test wrap with function failure sends single FAILED ping."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data(status="FAILED")))
        )

        def failing_fn() -> None:
            raise ValueError("Something went wrong")

        with pytest.raises(ValueError, match="Something went wrong"):
            bw.wrap("my-job", failing_fn)

        # Only ONE HTTP call
        assert len(route.calls) == 1

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "FAILED"
        assert body["error"] == "Something went wrong"
        assert "startedAt" in body
        assert "completedAt" in body

    @respx.mock
    def test_wrap_preserves_original_error_on_ping_failure(self, bw: BearWatch) -> None:
        """Test that wrap preserves original error even when ping fails."""
        respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(500, json={"success": False, "error": {"message": "Server error"}})
        )

        original_error = ValueError("Original business error")

        def failing_fn() -> None:
            raise original_error

        with pytest.raises(ValueError) as exc_info:
            bw.wrap("my-job", failing_fn)

        # Should throw the ORIGINAL error, not the server error
        assert exc_info.value is original_error


class TestContextManager:
    """Tests for context manager support."""

    @respx.mock
    def test_context_manager_close(self, bw: BearWatch) -> None:
        """Test that context manager closes client."""
        with bw:
            pass
        # Client should be closed (sync client not created yet, so nothing to check)


class TestAsyncMethods:
    """Tests for async methods."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_ping_async_success(self, bw: BearWatch) -> None:
        """Test successful async ping."""
        respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        response = await bw.ping_async("my-job")

        assert response["status"] == "SUCCESS"

    @respx.mock
    @pytest.mark.asyncio
    async def test_ping_async_with_timestamps(self, bw: BearWatch) -> None:
        """Test async ping with timestamps."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        started = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2024, 1, 1, 10, 0, 2, tzinfo=timezone.utc)
        await bw.ping_async("my-job", started_at=started, completed_at=completed)

        body = json.loads(route.calls[0].request.content)
        assert body["startedAt"] == "2024-01-01T10:00:00Z"
        assert body["completedAt"] == "2024-01-01T10:00:02Z"

    @respx.mock
    @pytest.mark.asyncio
    async def test_wrap_async_success(self, bw: BearWatch) -> None:
        """Test successful async wrap with single HTTP call."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        async def async_fn() -> str:
            return "async result"

        result = await bw.wrap_async("my-job", async_fn)

        assert result == "async result"
        # Only ONE HTTP call
        assert len(route.calls) == 1

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "SUCCESS"
        assert "startedAt" in body
        assert "completedAt" in body

    @respx.mock
    @pytest.mark.asyncio
    async def test_wrap_async_failure(self, bw: BearWatch) -> None:
        """Test async wrap with function failure."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data(status="FAILED")))
        )

        async def failing_async_fn() -> None:
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError, match="Async error"):
            await bw.wrap_async("my-job", failing_async_fn)

        # Only ONE HTTP call
        assert len(route.calls) == 1

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "FAILED"
        assert body["error"] == "Async error"
