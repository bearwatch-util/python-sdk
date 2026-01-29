"""BearWatch Python SDK - Job monitoring with heartbeat-based detection."""

from bearwatch.client import BearWatch
from bearwatch.config import BearWatchConfig
from bearwatch.errors import BearWatchError, ErrorCode, ErrorContext
from bearwatch.types import (
    HeartbeatResponse,
    PingOptions,
    RequestStatus,
    ResponseStatus,
    Status,
    WrapOptions,
)

__version__ = "0.1.1"

__all__ = [
    # Main client
    "BearWatch",
    # Configuration
    "BearWatchConfig",
    # Errors
    "BearWatchError",
    "ErrorCode",
    "ErrorContext",
    # Types
    "RequestStatus",
    "ResponseStatus",
    "Status",  # Backward compatibility alias for ResponseStatus
    "PingOptions",
    "WrapOptions",
    "HeartbeatResponse",
]
