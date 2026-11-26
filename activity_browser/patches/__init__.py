"""Process-start workarounds for upstream Qt / Python quirks.

Imported once from ``activity_browser.__init__`` **before** ``qtpy`` /
``PySide6``. Keep each fix tiny and documented (issue + upstream cause).

Library monkey-patches that can wait until the dependency is imported belong
in ``activity_browser.mod`` (ADR-0004). This package is only for workarounds
that must run at process start.
"""

from __future__ import annotations

import os


def pin_qt_api_pyside6() -> None:
    """Force qtpy onto PySide6 in mixed Qt envs (GH-1818).

    AB is PySide6-only. Without this, qtpy can select PySide2 when both are
    installed. ``setdefault`` preserves an explicit user override.
    """
    os.environ.setdefault("QT_API", "pyside6")


def harden_six_for_pyside() -> None:
    """Keep ``six.moves`` importable after PySide6 on buggy Python 3.12 reprs.

    shiboken's import hook calls ``inspect.getsource`` on newly imported
    modules. On CPython builds affected by gh-112414, ``repr()`` of
    ``six.moves`` then assumes ``loader._path`` and raises ``AttributeError``
    (not caught by shiboken) — the GH-1829 startup crash via
    astunparse/bw2parameters. A class-level ``_path`` is enough and is a no-op
    on fixed Pythons.
    """
    try:
        import six
    except ImportError:
        return
    if not hasattr(six._SixMetaPathImporter, "_path"):
        six._SixMetaPathImporter._path = []


def apply() -> None:
    pin_qt_api_pyside6()
    harden_six_for_pyside()


apply()
