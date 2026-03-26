import time
import asyncio
import functools
import logging
import threading
import inspect
import json

from .utils import must_retry

logger = logging.getLogger("repdeco")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _normalize(obj):
    try:
        return json.dumps(obj, sort_keys=True, default=str)
    except Exception:
        return repr(obj)


def make_key(func, args, kwargs):
    return (
        func.__module__,
        func.__name__,
        _normalize(args),
        _normalize(kwargs),
    )


class MemoryCache:
    def __init__(self):
        self.store = {}
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key in self.store:
                val, exp = self.store[key]
                if exp is None or time.time() < exp:
                    return val
                del self.store[key]
        return None

    def set(self, key, val, ttl):
        with self.lock:
            exp = time.time() + ttl if ttl else None
            self.store[key] = (val, exp)


class CircuitBreaker:
    def __init__(self, threshold, timeout):
        self.fail = 0
        self.threshold = threshold
        self.timeout = timeout
        self.open_until = 0
        self.half_open = False
        self.lock = threading.Lock()

    def check(self, name):
        with self.lock:
            now = time.time()
            if now < self.open_until:
                raise Exception(f"[Circuit OPEN] {name}")
            if self.open_until and now >= self.open_until:
                self.half_open = True

    def success(self):
        with self.lock:
            self.fail = 0
            self.open_until = 0
            self.half_open = False

    def fail_call(self, name):
        with self.lock:
            self.fail += 1
            if self.half_open or self.fail >= self.threshold:
                self.open_until = time.time() + self.timeout
                self.half_open = False
                logger.error(f"[Circuit OPEN] {name}")


class Repdeco:
    def __init__(
        self,
        cache_backend=None,
        enable_logging=True,
    ):
        self.cache = cache_backend or MemoryCache()
        self.enable_logging = enable_logging

    def repdeco(
        self,
        retry=0,
        retry_on=None,
        backoff=0,
        timeout=None,
        cache_ttl=0,
        cb_threshold=5,
        cb_timeout=10,
    ):
        def decorator(func):
            is_async = inspect.iscoroutinefunction(func)
            cb = CircuitBreaker(cb_threshold, cb_timeout)

            def log(msg):
                if self.enable_logging:
                    logger.info(msg)

            async def run_async(*args, **kwargs):
                name = func.__name__
                key = make_key(func, args, kwargs)

                cb.check(name)

                if cache_ttl:
                    cached = self.cache.get(key)
                    if cached is not None:
                        log(f"[cache hit] {name}")
                        return cached

                last_error = None

                for attempt in range(retry + 1):
                    try:
                        log(f"[call] {name} attempt={attempt+1}")

                        if timeout:
                            result = await asyncio.wait_for(
                                func(*args, **kwargs), timeout
                            )
                        else:
                            result = await func(*args, **kwargs)

                        cb.success()

                        if cache_ttl:
                            self.cache.set(key, result, cache_ttl)

                        return result

                    except Exception as e:
                        last_error = e
                        cb.fail_call(name)

                        if not must_retry(e, retry_on):
                            raise

                        if attempt < retry:
                            sleep = backoff * (2 ** attempt) if backoff else 1
                            await asyncio.sleep(sleep)

                raise last_error

            def run_sync(*args, **kwargs):
                name = func.__name__
                key = make_key(func, args, kwargs)

                cb.check(name)

                if cache_ttl:
                    cached = self.cache.get(key)
                    if cached is not None:
                        log(f"[cache hit] {name}")
                        return cached

                last_error = None

                for attempt in range(retry + 1):
                    try:
                        log(f"[call] {name} attempt={attempt+1}")

                        if timeout:
                            loop = asyncio.new_event_loop()
                            result = loop.run_until_complete(
                                asyncio.wait_for(func(*args, **kwargs), timeout)
                            )
                            loop.close()
                        else:
                            result = func(*args, **kwargs)

                        cb.success()

                        if cache_ttl:
                            self.cache.set(key, result, cache_ttl)

                        return result

                    except Exception as e:
                        last_error = e
                        cb.fail_call(name)

                        if not must_retry(e, retry_on):
                            raise

                        if attempt < retry:
                            sleep = backoff * (2 ** attempt) if backoff else 1
                            time.sleep(sleep)

                raise last_error

            return run_async if is_async else run_sync

        return decorator


_default = Repdeco()


def repdeco(*args, **kwargs):
    return _default.repdeco(*args, **kwargs)