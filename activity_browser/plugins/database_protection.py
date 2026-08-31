# -*- coding: utf-8 -*-
"""Host-owned temporary database protection for plugins."""
from __future__ import annotations

from contextlib import contextmanager
from threading import Lock
from typing import Dict, Iterable, Iterator, Optional, Tuple

_lock = Lock()
_refcounts: Dict[str, int] = {}
_meta: Dict[str, Tuple[str, str]] = {}


def is_database_protected(name: str) -> bool:
    if not name:
        return False
    with _lock:
        return _refcounts.get(name, 0) > 0


def protection_details(name: str) -> Optional[Tuple[str, str]]:
    """Return ``(plugin_id, reason)`` when protected, else ``None``."""
    with _lock:
        if _refcounts.get(name, 0) <= 0:
            return None
        return _meta.get(name)


def _register(names: Iterable[str], *, plugin_id: str, reason: str) -> list[str]:
    activated: list[str] = []
    with _lock:
        for name in names:
            if not name:
                continue
            prev = _refcounts.get(name, 0)
            _refcounts[name] = prev + 1
            _meta[name] = (plugin_id, reason or "")
            if prev == 0:
                activated.append(name)
    return activated


def _unregister(names: Iterable[str]) -> list[str]:
    released: list[str] = []
    with _lock:
        for name in names:
            if not name:
                continue
            count = _refcounts.get(name, 0)
            if count <= 0:
                continue
            count -= 1
            if count == 0:
                _refcounts.pop(name, None)
                _meta.pop(name, None)
                released.append(name)
            else:
                _refcounts[name] = count
    return released


def _notify_protection_changed(names: Iterable[str]) -> None:
    if not names:
        return
    from activity_browser import app
    import bw2data as bd

    for name in names:
        if name not in bd.databases:
            continue
        locked = bd.databases[name].get("read_only", True) or is_database_protected(name)
        app.signals.database_read_only_changed.emit(name, locked)


@contextmanager
def protect_databases(
    names: Iterable[str],
    *,
    plugin_id: str,
    reason: str = "",
) -> Iterator[None]:
    names_list = list(names)
    activated = _register(names_list, plugin_id=plugin_id, reason=reason)
    _notify_protection_changed(activated)
    try:
        yield
    finally:
        released = _unregister(names_list)
        _notify_protection_changed(released)


def find_protected_names(names: Iterable[str]) -> list[str]:
    return [name for name in names if is_database_protected(name)]


def format_protection_block_message(names: Iterable[str]) -> str:
    lines = ["The following databases are temporarily in use by a plugin and cannot be modified:"]
    for name in names:
        details = protection_details(name)
        if details:
            plugin_id, reason = details
            suffix = f" ({reason})" if reason else ""
            lines.append(f"• {name} — {plugin_id}{suffix}")
        else:
            lines.append(f"• {name}")
    return "\n".join(lines)


def database_is_editing_blocked(name: str) -> bool:
    """True when user edits should be blocked (read-only or plugin-protected)."""
    from activity_browser.bwutils.commontasks import database_is_locked

    return database_is_locked(name) or is_database_protected(name)


def reset_database_protection_for_tests() -> None:
    """Clear protection state (tests only)."""
    with _lock:
        _refcounts.clear()
        _meta.clear()
