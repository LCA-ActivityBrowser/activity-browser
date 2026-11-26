"""Regression tests for shiboken feature-hook / six.moves startup crash (#1829)."""

from __future__ import annotations


def test_patch_shiboken_feature_hook_swallows_attribute_error(monkeypatch):
    """Simulate CPython 3.12.0 module-repr bug escaping _mod_uses_pyside."""
    import shibokensupport.feature as feature
    from activity_browser.shiboken_compat import patch_shiboken_feature_hook

    def boom(_module):
        raise AttributeError("'_SixMetaPathImporter' object has no attribute '_path'")

    monkeypatch.setattr(feature, "_mod_uses_pyside", boom)
    assert patch_shiboken_feature_hook() is True
    assert feature._mod_uses_pyside(object()) is False
    assert getattr(feature._mod_uses_pyside, "_ab_six_moves_safe", False)


def test_patch_shiboken_feature_hook_is_idempotent():
    from activity_browser.shiboken_compat import patch_shiboken_feature_hook
    import shibokensupport.feature as feature

    assert patch_shiboken_feature_hook() is True
    first = feature._mod_uses_pyside
    assert patch_shiboken_feature_hook() is True
    assert feature._mod_uses_pyside is first


def test_patched_hook_survives_buggy_module_repr(monkeypatch):
    """End-to-end: six.moves import must not crash after PySide6 is loaded."""
    import importlib
    import importlib._bootstrap as bootstrap
    import sys

    import shibokensupport.feature as feature
    from activity_browser.shiboken_compat import patch_shiboken_feature_hook

    def buggy_repr(spec):
        name = "?" if spec.name is None else spec.name
        if spec.origin is None:
            if spec.loader is None:
                return f"<module {name!r}>"
            # Pre-3.12.1 behavior (gh-112414): assume every loader has _path.
            return f"<module {name!r} (namespace) from {list(spec.loader._path)}>"
        if spec.has_location:
            return f"<module {name!r} from {spec.origin!r}>"
        return f"<module {spec.name!r} ({spec.origin})>"

    monkeypatch.setattr(bootstrap, "_module_repr_from_spec", buggy_repr)
    assert patch_shiboken_feature_hook() is True

    # Force a fresh six.moves import so feature_imported re-inspects it.
    for key in list(sys.modules):
        if key == "six" or key.startswith("six."):
            del sys.modules[key]
    if hasattr(feature, "pyside_feature_dict"):
        for key in list(feature.pyside_feature_dict):
            if "six" in key:
                del feature.pyside_feature_dict[key]

    importlib.import_module("six.moves")
    from six.moves import cStringIO

    assert cStringIO is not None


def test_qt_api_defaults_to_pyside6():
    import os

    # activity_browser.__init__ sets this before importing bindings.
    assert os.environ.get("QT_API", "").lower() == "pyside6"
