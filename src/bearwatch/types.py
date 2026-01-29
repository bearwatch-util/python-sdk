"""Type definitions for BearWatch SDK."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypedDict


# Status types
# RequestStatus: values that SDK can send to the server
RequestStatus = Literal["RUNNING", "SUCCESS", "FAILED"]

# ResponseStatus: values that server can return (includes server-detected states)
ResponseStatus = Literal["RUNNING", "SUCCESS", "FAILED", "TIMEOUT", "MISSED"]

# Backward compatibility alias (deprecated, use ResponseStatus for responses)
Status = ResponseStatus


class PingOptions(TypedDict, total=False):
    """Options for ping operation."""

    status: RequestStatus
    output: str | None
    error: str | None
    started_at: datetime | str | None
    completed_at: datetime | str | None
    metadata: dict[str, Any] | None
    retry: bool


class WrapOptions(TypedDict, total=False):
    """Options for wrap operation."""

    output: str | None
    metadata: dict[str, Any] | None
    retry: bool


class HeartbeatResponse(TypedDict):
    """Response from heartbeat API endpoints.

    Note: The SDK unwraps the ApiResponse wrapper, returning only the data portion.
    """

    runId: str
    jobId: str
    status: ResponseStatus
    receivedAt: str  # ISO 8601
