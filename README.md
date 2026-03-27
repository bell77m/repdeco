# 🛡️ Repdeco

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-OS%20Independent-lightgrey.svg)](https://github.com/yourusername/repdeco)

**Repdeco** (Resilience & Protection Decorator) is a powerful, all-in-one Python decorator designed to make your functions bulletproof. Whether you are dealing with flaky APIs, unstable database connections, or heavy computations, `repdeco` has you covered.

It provides a unified, elegant interface for **Retries**, **Exponential Backoff**, **Timeouts**, **Circuit Breaking**, and **Memory Caching** — seamlessly supporting both `sync` and `async` functions.


## 🚀 Features

- **🔄 Retries & Backoff** — Automatically retry failing operations with optional exponential backoff.
- **⏱️ Timeouts** — Stop execution if a function takes too long (safely works for both `async` and `sync` functions using ThreadPool).
- **🔌 Circuit Breaker** — Prevent cascading failures by failing fast when a downstream system is down.
- **💾 Caching** — In-memory caching with Time-To-Live (TTL) to speed up repeated calls.
- **⚡ Sync & Async Ready** — Use the exact same `@repdeco` decorator for standard `def` and `async def`.
- **📝 Metadata Preserved** — Keeps your original function names and docstrings intact (`@functools.wraps` support).



## 📦 Installation

```bash
pip install repdeco
```



## 💡 Quick Start & Usage

Import the decorator into your project:

```python
import time
import asyncio
from repdeco.core import repdeco
```



### 1. Retries with Exponential Backoff

If the function raises an exception, it will retry up to `retry` times. The `backoff=1` means it will wait 1s, 2s, and 4s between attempts.

```python
@repdeco(retry=3, backoff=1)
def fetch_data():
    print("Fetching data...")
    raise ConnectionError("Network unstable")

# Will try 4 times total (1 initial + 3 retries) before raising the error.
```


### 2. Timeouts (Sync & Async)

Enforce a strict time limit. If the function exceeds `timeout` seconds, it will raise a `TimeoutError`.

```python
@repdeco(timeout=2)
def slow_sync_task():
    time.sleep(5)
    return "Done"

@repdeco(timeout=2)
async def slow_async_task():
    await asyncio.sleep(5)
    return "Done"
```


### 3. Circuit Breaker

If a function fails `cb_threshold` times in a row, the circuit **opens**. It immediately blocks further calls for `cb_timeout` seconds, raising an `Exception` instantly without even trying to run the failing function.

```python
@repdeco(cb_threshold=5, cb_timeout=60)
def fragile_api_call():
    # If this fails 5 times, it gets blocked for 60 seconds
    pass
```

**Circuit states:**

```
CLOSED (normal) → [N failures] → OPEN (blocked) → [timeout expires] → HALF-OPEN → [success] → CLOSED
```


### 4. Caching with TTL (Time-To-Live)

Cache the results of expensive function calls based on their arguments.

```python
@repdeco(cache_ttl=300)  # Cache for 5 minutes
def heavy_computation(x, y):
    print("Calculating...")
    time.sleep(3)
    return x * y

print(heavy_computation(5, 5))  # Takes 3 seconds → returns 25
print(heavy_computation(5, 5))  # Instant! (Returns cached 25)
```


### 5. The "All-in-One" Combo

You can combine all features to create highly resilient functions. The decorator evaluates logic in this order:

```
Cache → Circuit Breaker → Timeout → Retries
```

```python
@repdeco(
    retry=2,
    backoff=2,
    timeout=5,
    cache_ttl=60,
    cb_threshold=3,
    cb_timeout=30
)
async def resilient_web_scraper(url):
    # Your robust scraping logic here
    pass
```


## ⚙️ Configuration Parameters

| Parameter      | Type           | Default | Description                                                                                          |
|----------------|----------------|---------|------------------------------------------------------------------------------------------------------|
| `retry`        | `int`          | `0`     | Number of times to retry the function after an initial failure.                                      |
| `retry_on`     | `tuple`        | `None`  | Specific exception classes to catch and retry on (e.g., `(ConnectionError,)`). If `None`, retries on all exceptions. |
| `backoff`      | `int`/`float`  | `0`     | Base multiplier for exponential backoff sleep time (`backoff * 2^attempt`). `0` means retry immediately. |
| `timeout`      | `int`/`float`  | `None`  | Maximum seconds the function is allowed to run before raising a `TimeoutError`.                      |
| `cache_ttl`    | `int`/`float`  | `0`     | Time-To-Live in seconds for the in-memory cache. `0` disables caching.                               |
| `cb_threshold` | `int`          | `5`     | Number of consecutive failures before the Circuit Breaker opens.                                     |
| `cb_timeout`   | `int`/`float`  | `10`    | Seconds the Circuit Breaker remains open before attempting a half-open retry.                        |


## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.