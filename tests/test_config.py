"""Tests for BearWatchConfig."""

import pytest

from bearwatch.config import BearWatchConfig


class TestBearWatchConfig:
    """Tests for BearWatchConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = BearWatchConfig(api_key="test-key")

        assert config.api_key == "test-key"
        assert config.base_url == "https://api.bearwatch.dev"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 0.5

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = BearWatchConfig(
            api_key="custom-key",
            base_url="https://custom.api.com",
            timeout=60.0,
            max_retries=5,
            retry_delay=1.0,
        )

        assert config.api_key == "custom-key"
        assert config.base_url == "https://custom.api.com"
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.retry_delay == 1.0

    def test_empty_api_key_raises_error(self) -> None:
        """Test that empty api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key is required"):
            BearWatchConfig(api_key="")

    def test_invalid_timeout_raises_error(self) -> None:
        """Test that non-positive timeout raises ValueError."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            BearWatchConfig(api_key="test", timeout=0)

        with pytest.raises(ValueError, match="timeout must be positive"):
            BearWatchConfig(api_key="test", timeout=-1)

    def test_invalid_max_retries_raises_error(self) -> None:
        """Test that negative max_retries raises ValueError."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            BearWatchConfig(api_key="test", max_retries=-1)

    def test_zero_max_retries_allowed(self) -> None:
        """Test that zero max_retries is valid (no retries)."""
        config = BearWatchConfig(api_key="test", max_retries=0)
        assert config.max_retries == 0

    def test_invalid_retry_delay_raises_error(self) -> None:
        """Test that negative retry_delay raises ValueError."""
        with pytest.raises(ValueError, match="retry_delay must be non-negative"):
            BearWatchConfig(api_key="test", retry_delay=-1)

    def test_zero_retry_delay_allowed(self) -> None:
        """Test that zero retry_delay is valid (no delay)."""
        config = BearWatchConfig(api_key="test", retry_delay=0)
        assert config.retry_delay == 0
