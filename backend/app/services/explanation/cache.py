"""In-memory explanation cache keyed by verified-state fingerprint."""

from __future__ import annotations

from collections import OrderedDict

from app.services.explanation.schema import GroundedAnswer

_MAX = 256
_STORE: OrderedDict[str, GroundedAnswer] = OrderedDict()


def cache_get(key: str) -> GroundedAnswer | None:
    item = _STORE.get(key)
    if item is None:
        return None
    _STORE.move_to_end(key)
    return item.model_copy(deep=True)


def cache_set(key: str, value: GroundedAnswer) -> None:
    _STORE[key] = value.model_copy(deep=True)
    _STORE.move_to_end(key)
    while len(_STORE) > _MAX:
        _STORE.popitem(last=False)


def cache_clear() -> None:
    _STORE.clear()


def cache_size() -> int:
    return len(_STORE)
