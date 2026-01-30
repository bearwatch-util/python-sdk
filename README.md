# bearwatch

Official BearWatch SDK for Python - Job monitoring and alerting for indie developers.

## Table of Contents

- [Installation](#installation)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [ping](#ping---manual-status-reporting)
  - [wrap](#wrap---automatic-status-reporting)
- [Async Support](#async-support)
  - [Async Context Manager](#async-context-manager)
  - [ping_async](#ping_async)
  - [wrap_async](#wrap_async)
  - [Async Error Handling](#async-error-handling)
- [Configuration](#configuration)
- [Context Manager](#context-manager)
- [API Reference](#api-reference)
  - [BearWatch](#bearwatch-1)
  - [Types](#types)
  - [Errors](#errors)
- [Retry Policy](#retry-policy)
- [Error Handling](#error-handling)
- [Common Patterns](#common-patterns)
- [FAQ](#faq)
- [License](#license)

## Installation

```bash
pip install bearwatch
```

## Requirements

- **Python 3.9 or higher**
- **httpx >= 0.25.0** (installed automatically)

## Quick Start

### 1. Get API Key

Go to [BearWatch Dashboard](https://bearwatch.dev) → Project Settings → Create API Key (e.g., `bw_kI6t8QA21on0DKeRDlen8r2hzucVNL3WdAfaZgQdetY`).

### 2. Create a Job

Create a job in the dashboard. You'll get a job ID (24-character hex string, e.g., `507f1f77bcf86cd799439011`).

### 3. Install and Use

Let's assume you have a daily backup job that runs at 2:00 AM:

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from bearwatch import BearWatch

bw = BearWatch(api_key="your-api-key")

def backup_job():
    bw.wrap("507f1f77bcf86cd799439011", lambda: backup())

scheduler = BlockingScheduler()
scheduler.add_job(backup_job, "cron", hour=2)
scheduler.start()
```

## Usage

### ping - Manual Status Reporting

Use `ping` when you need fine-grained control over status reporting:

```python
def backup_job():
    try:
        backup()
        bw.ping("507f1f77bcf86cd799439011", status="SUCCESS")
    except Exception as e:
        bw.ping("507f1f77bcf86cd799439011", status="FAILED", error=str(e))
```

Include output and metadata:

```python
def backup_job():
    bytes_written = backup()
    bw.ping(
        "507f1f77bcf86cd799439011",
        status="SUCCESS",
        output=f"Backup completed: {bytes_written} bytes",
        metadata={
            "server": "backup-01",
            "region": "ap-northeast-2",
            "version": "1.2.0",
        },
    )
```

Return value:

```python
response = bw.ping("507f1f77bcf86cd799439011", status="SUCCESS")
# response:
# {
#     'runId': '684a1b2c3d4e5f6789012345',
#     'jobId': '507f1f77bcf86cd799439011',
#     'status': 'SUCCESS',
#     'receivedAt': '2024-01-15T09:30:00.123Z'
# }
```

#### PingOptions

| Option         | Type              | Default      | Description                              |
| -------------- | ----------------- | ------------ | ---------------------------------------- |
| `status`       | `RequestStatus`   | `"SUCCESS"`  | `"RUNNING"`, `"SUCCESS"`, or `"FAILED"`  |
| `output`       | `str`             | -            | Output message (max 10KB)                |
| `error`        | `str`             | -            | Error message for `FAILED` status (max 10KB) |
| `started_at`   | `datetime \| str` | current time | Job start time (ISO 8601 if string)      |
| `completed_at` | `datetime \| str` | current time | Job completion time (ISO 8601 if string) |
| `metadata`     | `dict[str, Any]`  | -            | Additional key-value pairs (max 10KB)    |
| `retry`        | `bool`            | `True`       | Set `False` to disable retry for this call |

> **Note**: `TIMEOUT` and `MISSED` are server-detected states and cannot be set in requests.

> **Size Limit**: `output`, `error`, and `metadata` fields have a 10KB size limit. If exceeded, the server automatically truncates the data (no error is returned). For `output` and `error`, the string is truncated. For `metadata`, the entire field is set to `null` if it exceeds the limit.

### wrap - Automatic Status Reporting

Wraps a function and automatically:
- Measures `started_at` and `completed_at`
- Reports `SUCCESS` or `FAILED` based on whether the function completes or throws

```python
# Pass function directly (no arguments)
bw.wrap("507f1f77bcf86cd799439011", backup)

# Use lambda for functions with arguments
bw.wrap("507f1f77bcf86cd799439011", lambda: backup(path="/data"))
```

Include output and metadata:

```python
def backup_job():
    bw.wrap(
        "507f1f77bcf86cd799439011",
        lambda: backup(),
        output="Daily backup completed",
        metadata={
            "server": "backup-01",
            "region": "ap-northeast-2",
        },
    )
```

Return value (returns the wrapped function's result):

```python
result = bw.wrap("507f1f77bcf86cd799439011", lambda: "done")
# result: 'done'

count = bw.wrap("507f1f77bcf86cd799439011", lambda: len(records))
# count: 42
```

#### WrapOptions

| Option     | Type             | Default | Description                         |
| ---------- | ---------------- | ------- | ----------------------------------- |
| `output`   | `str`            | -       | Output message (max 10KB)           |
| `metadata` | `dict[str, Any]` | -       | Additional key-value pairs (max 10KB) |
| `retry`    | `bool`           | `True`  | Set `False` to disable retry for this call |

> **Size Limit**: `output` and `metadata` fields have a 10KB size limit. If exceeded, the server automatically truncates the data (no error is returned). For `output`, the string is truncated. For `metadata`, the entire field is set to `null` if it exceeds the limit.

**Error handling behavior:**
- On success: reports `SUCCESS` with execution duration
- On error: reports `FAILED` with error message, then **re-raises the original exception**

```python
def backup_job():
    try:
        bw.wrap("507f1f77bcf86cd799439011", lambda: backup())
    except Exception as e:
        # BearWatch already reported FAILED status
        # You can add additional error handling here
        logger.error(e)
```

> **Tip**: Use `wrap` for most cases. Use `ping` when you need more control (e.g., reporting RUNNING status for long jobs).

## Async Support

The SDK provides async versions of all methods for use with `asyncio`, FastAPI, and other async frameworks.

### Async Context Manager

Use `async with` for automatic resource cleanup:

```python
async with BearWatch(api_key="your-api-key") as bw:
    await bw.ping_async("507f1f77bcf86cd799439011")
    # Resources automatically cleaned up on exit
```

Without context manager (remember to close):

```python
bw = BearWatch(api_key="your-api-key")
try:
    await bw.ping_async("507f1f77bcf86cd799439011")
finally:
    await bw.aclose()
```

### ping_async

```python
async with BearWatch(api_key="your-api-key") as bw:
    # Simple success
    await bw.ping_async("507f1f77bcf86cd799439011")

    # With options
    await bw.ping_async(
        "507f1f77bcf86cd799439011",
        status="FAILED",
        error="Connection timeout",
        metadata={"attempt": 3},
    )
```

### wrap_async

Wraps an async function and automatically:
- Measures `started_at` and `completed_at`
- Reports `SUCCESS` or `FAILED` based on whether the function completes or raises

```python
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as resp:
            return await resp.json()

async with BearWatch(api_key="your-api-key") as bw:
    # Basic usage
    result = await bw.wrap_async("507f1f77bcf86cd799439011", fetch_data)

    # With output and metadata
    result = await bw.wrap_async(
        "507f1f77bcf86cd799439011",
        fetch_data,
        output="Fetched 1000 records",
        metadata={"source": "api.example.com"},
    )
```

### Async Error Handling

**For `ping_async`**: raises `BearWatchError` on failure.

```python
from bearwatch import BearWatch, BearWatchError

async with BearWatch(api_key="your-api-key") as bw:
    try:
        await bw.ping_async("507f1f77bcf86cd799439011")
    except BearWatchError as e:
        print(f"Failed to report: {e.code}")
```

**For `wrap_async`**: reports failure to BearWatch, then re-raises the original exception.

```python
async with BearWatch(api_key="your-api-key") as bw:
    try:
        await bw.wrap_async("507f1f77bcf86cd799439011", async_backup)
    except BackupError as e:
        # BearWatch already reported FAILED status
        # Handle your application error here
        logger.error(f"Backup failed: {e}")
```

> **Note**: If `wrap_async` fails to report to BearWatch (network error, etc.), the original exception is still raised. The SDK silently ignores reporting errors to preserve the original exception.

## Configuration

```python
bw = BearWatch(
    api_key="your-api-key",

    # Optional (defaults shown)
    timeout=30.0,       # 30 seconds
    max_retries=3,
    retry_delay=0.5,    # 500ms base delay
)
```

| Option        | Type    | Required | Default  | Description               |
| ------------- | ------- | -------- | -------- | ------------------------- |
| `api_key`     | `str`   | Yes      | -        | API key for authentication |
| `timeout`     | `float` | No       | `30.0`   | Request timeout (seconds) |
| `max_retries` | `int`   | No       | `3`      | Max retry attempts        |
| `retry_delay` | `float` | No       | `0.5`    | Initial retry delay (seconds) |

## Context Manager

Use context managers for automatic resource cleanup:

```python
# Sync
with BearWatch(api_key="your-api-key") as bw:
    bw.ping("507f1f77bcf86cd799439011")

# Async
async with BearWatch(api_key="your-api-key") as bw:
    await bw.ping_async("507f1f77bcf86cd799439011")
```

## API Reference

### BearWatch

```python
class BearWatch:
    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ) -> None: ...

    @classmethod
    def create(cls, config: BearWatchConfig) -> BearWatch: ...

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
    ) -> HeartbeatResponse: ...

    def wrap(
        self,
        job_id: str,
        fn: Callable[[], T],
        *,
        output: str | None = None,
        metadata: dict[str, Any] | None = None,
        retry: bool = True,
    ) -> T: ...

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
    ) -> HeartbeatResponse: ...

    async def wrap_async(
        self,
        job_id: str,
        fn: Callable[[], Awaitable[T]],
        *,
        output: str | None = None,
        metadata: dict[str, Any] | None = None,
        retry: bool = True,
    ) -> T: ...

    def close(self) -> None: ...
    async def aclose(self) -> None: ...
```

### Types

#### Status Types

```python
# Status that SDK can send to the server
RequestStatus = Literal["RUNNING", "SUCCESS", "FAILED"]

# Status that server can return (includes server-detected states)
ResponseStatus = Literal["RUNNING", "SUCCESS", "FAILED", "TIMEOUT", "MISSED"]
```

#### HeartbeatResponse

Return value of `ping()` and `wrap()` methods:

```python
class HeartbeatResponse(TypedDict):
    runId: str           # Generated run ID
    jobId: str           # Job ID
    status: ResponseStatus
    receivedAt: str      # Server received time (ISO 8601)
```

#### BearWatchConfig

Configuration for `BearWatch.create()` method:

```python
@dataclass
class BearWatchConfig:
    api_key: str              # Required - API authentication key
    timeout: float = 30.0     # Request timeout in seconds
    max_retries: int = 3      # Maximum retry attempts
    retry_delay: float = 0.5  # Retry interval in seconds (exponential backoff)
```

### Errors

#### BearWatchError

```python
class BearWatchError(Exception):
    code: ErrorCode           # Error code
    status_code: int | None   # HTTP status code
    context: ErrorContext | None
    response_body: str | None # Response body for debugging
```

#### ErrorCode

```python
ErrorCode = Literal[
    "INVALID_API_KEY",   # 401 - Invalid API key
    "JOB_NOT_FOUND",     # 404 - Job not found
    "RATE_LIMITED",      # 429 - Rate limit exceeded
    "SERVER_ERROR",      # 5xx - Server error
    "INVALID_RESPONSE",  # Unexpected response format
    "NETWORK_ERROR",     # Network failure
    "TIMEOUT",           # Request timeout
]
```

#### ErrorContext

```python
@dataclass
class ErrorContext:
    job_id: str | None = None
    run_id: str | None = None
    operation: str | None = None  # "ping", "wrap", etc.
```

#### Imports

```python
from bearwatch import (
    BearWatch,
    BearWatchConfig,
    BearWatchError,
    ErrorCode,
    ErrorContext,
    HeartbeatResponse,
    PingOptions,
    WrapOptions,
    RequestStatus,
    ResponseStatus,
)
```

## Retry Policy

| Method         | Default Retry | Reason                       |
| -------------- | ------------- | ---------------------------- |
| `ping()`       | Enabled       | Idempotent operation         |
| `ping_async()` | Enabled       | Idempotent operation         |
| `wrap()`       | Enabled       | Uses ping() internally       |
| `wrap_async()` | Enabled       | Uses ping_async() internally |

### Retry Behavior

- **Exponential backoff**: 500ms → 1000ms → 2000ms
- **429 Rate Limit**: Respects `Retry-After` header (rate limit: 100 requests/minute per API key)
- **5xx Server Errors**: Retries with backoff
- **401/404**: No retry (client errors)

### Disable Retry

Use `retry=False` to skip retries for a specific call, regardless of the `max_retries` setting:

```python
bw.ping("507f1f77bcf86cd799439011", retry=False)
```

## Error Handling

When the SDK fails to communicate with BearWatch (network failure, server down, invalid API key, etc.), it raises a `BearWatchError`:

```python
from bearwatch import BearWatch, BearWatchError

try:
    bw.ping("507f1f77bcf86cd799439011")
except BearWatchError as e:
    # SDK failed to report to BearWatch
    print(f"Code: {e.code}")
    print(f"Status: {e.status_code}")
    print(f"Context: {e.context}")
```

### Error Codes

| Code               | Description                | Retry   |
| ------------------ | -------------------------- | ------- |
| `INVALID_API_KEY`  | 401 - Invalid API key      | No      |
| `JOB_NOT_FOUND`    | 404 - Job not found        | No      |
| `RATE_LIMITED`     | 429 - Rate limit reached   | Yes     |
| `SERVER_ERROR`     | 5xx - Server error         | Yes     |
| `INVALID_RESPONSE` | Unexpected response format | No      |
| `NETWORK_ERROR`    | Network failure            | Yes     |
| `TIMEOUT`          | Request timed out          | Yes     |

## Common Patterns

### APScheduler

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from bearwatch import BearWatch

bw = BearWatch(api_key="your-api-key")

def backup_job():
    bw.wrap("6848c9e5f8a2b3d4e5f60001", lambda: backup())

scheduler = BlockingScheduler()
scheduler.add_job(backup_job, "cron", hour=3)
scheduler.start()
```

### Celery Beat

```python
from celery import Celery
from bearwatch import BearWatch

app = Celery("tasks")
bw = BearWatch(api_key="your-api-key")

@app.task
def backup_task():
    bw.wrap("6848c9e5f8a2b3d4e5f60002", lambda: backup())
```

### AWS Lambda (EventBridge Scheduler)

```python
import os
from bearwatch import BearWatch

bw = BearWatch(api_key=os.environ["BEARWATCH_API_KEY"])

def handler(event, context):
    bw.wrap("6848c9e5f8a2b3d4e5f60003", lambda: backup())
```

### Long-Running Jobs

```python
from datetime import datetime, timezone

def run_backup():
    job_id = "6848c9e5f8a2b3d4e5f60004"
    started_at = datetime.now(timezone.utc)

    bw.ping(job_id, status="RUNNING")

    try:
        backup()
        bw.ping(
            job_id,
            status="SUCCESS",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        bw.ping(
            job_id,
            status="FAILED",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            error=str(e),
        )
        raise
```

## FAQ

**Q: Do I need to create jobs in the dashboard first?**
A: Yes, create a job in the [BearWatch Dashboard](https://bearwatch.dev) first to get a job ID.

**Q: What's the difference between `wrap` and `ping`?**
A: `wrap` automatically measures execution time and reports SUCCESS/FAILED based on whether the function completes or raises an exception. `ping` gives you manual control over when and what to report.

**Q: What happens if the SDK fails to report (network error)?**
A: By default, the SDK attempts up to 4 times total (1 initial + 3 retries) with exponential backoff. If all attempts fail, `ping` raises a `BearWatchError`. For `wrap`, the original function's exception takes priority and is always re-raised.

**Q: Can I use this with async frameworks like FastAPI?**
A: Yes, use `ping_async` and `wrap_async` for async contexts.

## License

MIT
