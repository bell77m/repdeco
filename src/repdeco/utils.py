import json
import hashlib

def make_cache_key(func, args, kwargs):
    try:
        raw = json.dumps({
            "func": func.__name__,
            "args": args,
            "kwargs": kwargs
        }, sort_keys=True, default=str)
    except Exception:
        raw = str((func.__name__, args, kwargs))

    return hashlib.sha256(raw.encode()).hexdigest()


def must_retry(error, retry_on):
    if retry_on is None:
        return True
    return any(isinstance(error, e) for e in retry_on)