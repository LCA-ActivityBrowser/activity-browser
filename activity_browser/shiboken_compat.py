"""Compatibility shims for PySide6 / shiboken6 import hooks."""

from __future__ import annotations


def patch_shiboken_feature_hook() -> bool:
    """Make shiboken's post-import feature hook tolerate ``six.moves``.

    PySide6 registers a ``feature_imported`` hook that calls
    ``inspect.getsource`` on every newly imported module to decide whether it
    uses PySide. On Python 3.12.0 (CPython gh-112414), ``repr()`` of a module
    whose loader is ``six._SixMetaPathImporter`` raises::

        AttributeError: '_SixMetaPathImporter' object has no attribute '_path'

    That exception is not among the ``TypeError`` / ``OSError`` /
    ``SyntaxError`` handlers inside ``_mod_uses_pyside``, so Brightway startup
    aborts while importing ``bw2parameters`` → ``astunparse`` → ``six.moves``
    (GitHub issue #1829).

    Returns
    -------
    bool
        ``True`` when the hook was patched (or was already safe).
    """
    try:
        import shibokensupport.feature as feature
    except ImportError:
        return False

    original = feature._mod_uses_pyside
    if getattr(original, "_ab_six_moves_safe", False):
        return True

    def _mod_uses_pyside_safe(module):
        try:
            return original(module)
        except Exception:
            # Heuristic only: treat uninspectable modules as non-PySide.
            return False

    _mod_uses_pyside_safe._ab_six_moves_safe = True  # type: ignore[attr-defined]
    feature._mod_uses_pyside = _mod_uses_pyside_safe
    return True
