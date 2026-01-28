"""Configuration for BearWatch SDK."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BearWatchConfig:
    """Configuration options for BearWatch client.

    Args:
        api_key: API key for authentication (X-API-Key header).
        base_url: Base URL for the BearWatch API.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts for retryable errors.
        retry_delay: Initial delay between retries in seconds (exponential backoff).
    """

    api_key: str
    base_url: str = "https://api.bearwatch.dev"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 0.5

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.api_key:
            raise ValueError("api_key is required")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
