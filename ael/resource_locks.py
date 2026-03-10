from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterable


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
def claim(keys: Iterable[str] | None):
    normalized = normalize_keys(keys)
    locks = [_get_lock(key) for key in normalized]
    for lock in locks:
        lock.acquire()
    try:
        yield normalized
    finally:
        for lock in reversed(locks):
            lock.release()
