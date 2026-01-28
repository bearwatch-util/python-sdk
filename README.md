# BearWatch Python SDK

Python SDK for BearWatch - Job monitoring with heartbeat-based detection.

## Installation

```bash
pip install bearwatch
```

## Quick Start

```python
from bearwatch import BearWatch

# Initialize client
bw = BearWatch(api_key="your-api-key")

# Simple heartbeat
bw.ping("my-job")

# With automatic timing (wrap)
result = bw.wrap("my-job", lambda: do_work())
# Automatically sends SUCCESS on completion, FAILED on exception
```

## Usage

### Simple Ping

```python
# Success ping
bw.ping("my-job")

# Report failure with error message
bw.ping("my-job", status="FAILED", error="Database connection failed")
```

### Ping with Options

Include additional details with your heartbeat:

```python
bw.ping(
    "my-job",
    status="SUCCESS",
    output="Processed 100 records",
    metadata={"record_count": 100, "source": "postgres"},
)

# With manual timing
from datetime import datetime, timezone

started_at = datetime.now(timezone.utc)
do_work()
bw.ping(
    "my-job",
    status="SUCCESS",
    started_at=started_at,
    completed_at=datetime.now(timezone.utc),
)
```

#### Ping Options

| Option         | Type                      | Description                                |
| -------------- | ------------------------- | ------------------------------------------ |
| `status`       | `RequestStatus`           | Job status (default: `"SUCCESS"`)          |
| `output`       | `str`                     | Output message                             |
| `error`        | `str`                     | Error message (for `FAILED` status)        |
| `started_at`   | `datetime \| str`         | Job start time (auto-set if not provided)  |
| `completed_at` | `datetime \| str`         | Job completion time (auto-set if not provided) |
| `metadata`     | `dict[str, Any]`          | Additional key-value pairs                 |
| `retry`        | `bool`                    | Enable/disable retry (default: `True`)     |

### Wrap Pattern

Automatically measures execution time and reports success or failure:

```python
# Sync
result = bw.wrap("my-job", lambda: do_work())

# With return value
count = bw.wrap("count-job", lambda: count_records())
```

## Async Support

```python
# Async ping
await bw.ping_async("my-job")

# Async ping with options
await bw.ping_async("my-job", status="FAILED", error="Timeout")

# Async wrap
result = await bw.wrap_async("my-job", async_do_work)
```

## Configuration

```python
bw = BearWatch(
    api_key="your-api-key",
    base_url="https://api.bearwatch.dev",  # Default
    timeout=30.0,                          # Seconds
    max_retries=3,
    retry_delay=0.5,                       # Seconds
)
```

## Context Manager

Use context managers for automatic resource cleanup:

```python
# Sync
with BearWatch(api_key="your-api-key") as bw:
    bw.ping("my-job")

# Async
async with BearWatch(api_key="your-api-key") as bw:
    await bw.ping_async("my-job")
```

## Retry Policy

| Method         | Default Retry | Reason                       |
| -------------- | ------------- | ---------------------------- |
| `ping()`       | Yes           | Idempotent operation         |
| `ping_async()` | Yes           | Idempotent operation         |
| `wrap()`       | Yes           | Uses ping() internally       |
| `wrap_async()` | Yes           | Uses ping_async() internally |

### Retry Configuration

```python
bw = BearWatch(
    api_key="...",
    max_retries=3,       # Default: 3
    retry_delay=0.5,     # Initial delay in seconds
)

# Disable retry per-call
bw.ping("my-job", retry=False)
```

### Retryable Errors

- 429 (Rate Limited) - respects Retry-After header
- 5xx (Server Error) - exponential backoff
- Network errors

### Non-Retryable Errors

- 401 (Invalid API Key)
- 404 (Job Not Found)

## Error Handling

```python
from bearwatch import BearWatch, BearWatchError

try:
    bw.ping("my-job")
except BearWatchError as e:
    print(f"Code: {e.code}")
    print(f"Status: {e.status_code}")
    print(f"Context: {e.context}")
```

## Type Definitions

```python
from bearwatch import (
    BearWatch,
    BearWatchConfig,
    BearWatchError,
    ErrorContext,
    HeartbeatResponse,
    PingOptions,
    RequestStatus,
    ResponseStatus,
    Status,  # Alias for ResponseStatus
)
```

## License

MIT
