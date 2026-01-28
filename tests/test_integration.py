"""Integration tests for BearWatch SDK."""

import json

import pytest
import respx
from httpx import Response

from bearwatch import BearWatch, BearWatchError


@pytest.fixture
def bw() -> BearWatch:
    """Create a BearWatch client for testing."""
    return BearWatch(
        api_key="test-api-key",
        base_url="https://api.test.com",
        max_retries=2,
        retry_delay=0.01,  # Fast retries for tests
    )


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


class TestRetryBehavior:
    """Tests for retry behavior."""

    @respx.mock
    def test_retry_on_429(self, bw: BearWatch) -> None:
        """Test retry on 429 rate limit."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat")
        route.side_effect = [
            Response(
                429,
                json={"success": False, "error": {"code": "RATE_LIMITED"}},
                headers={"Retry-After": "0.01"},
            ),
            Response(200, json=_api_response(_heartbeat_data())),
        ]

        response = bw.ping("my-job")

        assert response["status"] == "SUCCESS"
        assert route.call_count == 2

    @respx.mock
    def test_retry_on_500(self, bw: BearWatch) -> None:
        """Test retry on 500 server error."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat")
        route.side_effect = [
            Response(
                500,
                json={"success": False, "error": {"code": "SERVER_ERROR"}},
            ),
            Response(200, json=_api_response(_heartbeat_data())),
        ]

        response = bw.ping("my-job")

        assert response["status"] == "SUCCESS"
        assert route.call_count == 2

    @respx.mock
    def test_no_retry_on_401(self, bw: BearWatch) -> None:
        """Test no retry on 401 unauthorized."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(
                401,
                json={"success": False, "error": {"code": "INVALID_API_KEY"}},
            )
        )

        with pytest.raises(BearWatchError) as exc_info:
            bw.ping("my-job")

        assert exc_info.value.code == "INVALID_API_KEY"
        assert route.call_count == 1  # No retry

    @respx.mock
    def test_no_retry_on_404(self, bw: BearWatch) -> None:
        """Test no retry on 404 not found."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/unknown/heartbeat").mock(
            return_value=Response(
                404,
                json={"success": False, "error": {"code": "JOB_NOT_FOUND"}},
            )
        )

        with pytest.raises(BearWatchError) as exc_info:
            bw.ping("unknown")

        assert exc_info.value.code == "JOB_NOT_FOUND"
        assert route.call_count == 1  # No retry

    @respx.mock
    def test_max_retries_exceeded(self, bw: BearWatch) -> None:
        """Test that max retries are enforced."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(
                500,
                json={"success": False, "error": {"code": "SERVER_ERROR"}},
            )
        )

        with pytest.raises(BearWatchError) as exc_info:
            bw.ping("my-job")

        assert exc_info.value.code == "SERVER_ERROR"
        # 1 initial + 2 retries = 3 total calls
        assert route.call_count == 3

    @respx.mock
    def test_retry_disabled(self, bw: BearWatch) -> None:
        """Test retry can be disabled per-call."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(
                500,
                json={"success": False, "error": {"code": "SERVER_ERROR"}},
            )
        )

        with pytest.raises(BearWatchError):
            bw.ping("my-job", retry=False)

        assert route.call_count == 1  # No retry


class TestWrapWorkflow:
    """Tests for wrap() workflow with single HTTP call."""

    @respx.mock
    def test_wrap_success_single_call(self, bw: BearWatch) -> None:
        """Test wrap sends single HTTP call on success."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        result = bw.wrap("my-job", lambda: "processed")

        assert result == "processed"
        # Only ONE HTTP call
        assert route.call_count == 1

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "SUCCESS"
        assert "startedAt" in body
        assert "completedAt" in body

    @respx.mock
    def test_wrap_failure_single_call(self, bw: BearWatch) -> None:
        """Test wrap sends single HTTP call on failure."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data(status="FAILED")))
        )

        with pytest.raises(ValueError, match="Computation failed"):
            bw.wrap("my-job", lambda: exec('raise ValueError("Computation failed")'))

        # Only ONE HTTP call
        assert route.call_count == 1

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "FAILED"
        assert "error" in body
        assert "startedAt" in body
        assert "completedAt" in body

    @respx.mock
    def test_wrap_measures_timing(self, bw: BearWatch) -> None:
        """Test wrap measures execution timing."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        import time
        from datetime import datetime

        def slow_work() -> str:
            time.sleep(0.05)  # 50ms
            return "done"

        result = bw.wrap("my-job", slow_work)

        assert result == "done"
        body = json.loads(route.calls[0].request.content)
        # Verify timestamps are present
        assert "startedAt" in body
        assert "completedAt" in body
        # Calculate duration from timestamps
        started = datetime.fromisoformat(body["startedAt"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(body["completedAt"].replace("Z", "+00:00"))
        duration_ms = (completed - started).total_seconds() * 1000
        assert duration_ms >= 50


class TestPingWithTimestamps:
    """Tests for ping with manual timestamps."""

    @respx.mock
    def test_ping_with_timestamps(self, bw: BearWatch) -> None:
        """Test ping with manual startedAt/completedAt."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        import time
        from datetime import datetime, timezone

        started_at = datetime.now(timezone.utc)
        time.sleep(0.02)  # 20ms
        completed_at = datetime.now(timezone.utc)

        bw.ping("my-job", started_at=started_at, completed_at=completed_at, output="Manual timing")

        body = json.loads(route.calls[0].request.content)
        assert "startedAt" in body
        assert "completedAt" in body
        assert body["output"] == "Manual timing"


class TestErrorContext:
    """Tests for error context."""

    @respx.mock
    def test_error_contains_context(self, bw: BearWatch) -> None:
        """Test that errors contain context information."""
        respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(
                404,
                json={"success": False, "error": {"code": "JOB_NOT_FOUND"}},
            )
        )

        with pytest.raises(BearWatchError) as exc_info:
            bw.ping("my-job", retry=False)

        error = exc_info.value
        assert error.context is not None
        assert error.context.job_id == "my-job"
        assert error.context.operation == "ping"


class TestAsyncIntegration:
    """Async integration tests."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_wrap_success(self, bw: BearWatch) -> None:
        """Test async wrap with single HTTP call."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data()))
        )

        async def async_work() -> str:
            return "async result"

        result = await bw.wrap_async("my-job", async_work)

        assert result == "async result"
        # Only ONE HTTP call
        assert route.call_count == 1

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "SUCCESS"
        assert "startedAt" in body
        assert "completedAt" in body

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_wrap_failure(self, bw: BearWatch) -> None:
        """Test async wrap failure with single HTTP call."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat").mock(
            return_value=Response(200, json=_api_response(_heartbeat_data(status="FAILED")))
        )

        async def failing_work() -> None:
            raise RuntimeError("Async failure")

        with pytest.raises(RuntimeError, match="Async failure"):
            await bw.wrap_async("my-job", failing_work)

        # Only ONE HTTP call
        assert route.call_count == 1

        body = json.loads(route.calls[0].request.content)
        assert body["status"] == "FAILED"
        assert body["error"] == "Async failure"

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_retry_on_429(self, bw: BearWatch) -> None:
        """Test async retry on 429."""
        route = respx.post("https://api.test.com/api/v1/ingest/jobs/my-job/heartbeat")
        route.side_effect = [
            Response(
                429,
                json={"success": False, "error": {"code": "RATE_LIMITED"}},
                headers={"Retry-After": "0.01"},
            ),
            Response(200, json=_api_response(_heartbeat_data())),
        ]

        response = await bw.ping_async("my-job")

        assert response["status"] == "SUCCESS"
        assert route.call_count == 2
