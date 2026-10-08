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
    """Run *sync* on the next event-loop tick (coalesced per *owner*).

    Uses ``QTimer.singleShot(0, ...)`` rather than
    ``thread().eventDispatcher().awake``, which can raise under PySide6/shiboken
    when the C++ dispatcher wrapper is already deleted (#1752).
    """
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

    QtCore.QTimer.singleShot(0, slot)
