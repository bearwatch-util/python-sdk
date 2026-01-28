"""BearWatch Python SDK - Job monitoring with heartbeat-based detection."""

from bearwatch.client import BearWatch
from bearwatch.config import BearWatchConfig
from bearwatch.errors import BearWatchError, ErrorContext
from bearwatch.types import (
    HeartbeatResponse,
    PingOptions,
    RequestStatus,
    ResponseStatus,
    Status,
)

__version__ = "0.1.0"

__all__ = [
    # Main client
    "BearWatch",
    # Configuration
    "BearWatchConfig",
    # Errors
    "BearWatchError",
    "ErrorContext",
    # Types
    "RequestStatus",
    "ResponseStatus",
    "Status",  # Backward compatibility alias for ResponseStatus
    "PingOptions",
    "HeartbeatResponse",
]
