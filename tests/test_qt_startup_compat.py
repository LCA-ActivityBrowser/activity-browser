"""Startup compatibility shims for Qt binding selection and six×PySide6."""
import importlib
import os
import sys

import pytest

from activity_browser.patches import harden_six_for_pyside


def test_qt_api_defaults_to_pyside6():
    import activity_browser  # noqa: F401 — applies patches.pin_qt_api_pyside6

    assert os.environ.get("QT_API") == "pyside6"


def test_harden_six_adds_path_on_meta_path_importer():
    import six

    # Simulate a clean six importer (as on first process start).
    if hasattr(six._SixMetaPathImporter, "_path"):
        delattr(six._SixMetaPathImporter, "_path")

    harden_six_for_pyside()
    assert hasattr(six._SixMetaPathImporter, "_path")
    assert six._SixMetaPathImporter._path == []


def test_six_moves_survives_buggy_cpython_module_repr(monkeypatch):
    """Regression for GH-1829: shiboken + six.moves on CPython gh-112414."""
    import importlib._bootstrap as bootstrap
    import six

    def buggy_repr(spec):
        name = "?" if spec.name is None else spec.name
        if spec.origin is None:
            if spec.loader is None:
                return f"<module {name!r}>"
            return f"<module {name!r} (namespace) from {list(spec.loader._path)}>"
        return f"<module {name!r} from {spec.origin!r}>"

    monkeypatch.setattr(bootstrap, "_module_repr_from_spec", buggy_repr)

    if hasattr(six._SixMetaPathImporter, "_path"):
        delattr(six._SixMetaPathImporter, "_path")

    # Drop cached modules so the next import re-enters six.moves + shiboken.
    for key in list(sys.modules):
        if key == "astunparse" or key.startswith("astunparse.") or key.startswith(
            "six.moves"
        ):
            del sys.modules[key]

    import PySide6.QtCore  # noqa: F401 — install shiboken import hook

    with pytest.raises(AttributeError, match="_path"):
        importlib.import_module("astunparse")

    for key in list(sys.modules):
        if key == "astunparse" or key.startswith("astunparse.") or key.startswith(
            "six.moves"
        ):
            del sys.modules[key]

    harden_six_for_pyside()
    importlib.import_module("astunparse")  # must not raise
