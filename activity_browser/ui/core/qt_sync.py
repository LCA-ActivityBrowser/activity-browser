"""Helpers for deferred Qt widget sync without touching deleted C++ objects."""

from __future__ import annotations

from collections.abc import Callable

from qtpy import QtCore


def qt_is_valid(obj) -> bool:
    """Return whether *obj* is still backed by a live Qt C++ object."""
    if obj is None:
        return False
    try:
        from shiboken6 import isValid
    except ImportError:
        from shiboken2 import isValid
    try:
        return bool(isValid(obj))
    except Exception:
        return False


def schedule_awake_sync(
    owner: QtCore.QObject,
    sync: Callable[[], None],
    *,
    flag_attr: str = "_populate_later_flag",
) -> None:
    """Run *sync* on the next GUI-thread awake event (coalesced per *owner*)."""
    if not qt_is_valid(owner):
        return
    if getattr(owner, flag_attr, False):
        return
    setattr(owner, flag_attr, True)

    def slot():
        setattr(owner, flag_attr, False)
        if not qt_is_valid(owner):
            return
        try:
            sync()
        except RuntimeError:
            pass
        try:
            owner.thread().eventDispatcher().awake.disconnect(slot)
        except (TypeError, RuntimeError):
            pass

    owner.thread().eventDispatcher().awake.connect(slot)
