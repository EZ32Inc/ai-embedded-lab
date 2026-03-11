from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from typing import Callable, Iterable


_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[str, threading.Lock] = {}


def _get_lock(key: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


def normalize_keys(keys: Iterable[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in keys or []:
        key = str(raw or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    out.sort()
    return out


@contextmanager
def claim(
    keys: Iterable[str] | None,
    *,
    on_wait: Callable[[str], None] | None = None,
    poll_interval_s: float = 0.05,
):
    normalized = normalize_keys(keys)
    locks = [(key, _get_lock(key)) for key in normalized]
    for key, lock in locks:
        notified = False
        while True:
            if lock.acquire(blocking=False):
                break
            if not notified and on_wait is not None:
                on_wait(key)
                notified = True
            time.sleep(max(0.0, poll_interval_s))
    try:
        yield normalized
    finally:
        for _key, lock in reversed(locks):
            lock.release()
