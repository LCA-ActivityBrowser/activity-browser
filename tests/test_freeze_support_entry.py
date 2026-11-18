"""Frozen Windows builds must divert multiprocessing workers before the GUI."""

from pathlib import Path
from types import SimpleNamespace

import activity_browser


REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRY_SCRIPT = REPO_ROOT / "run-activity-browser.py"


def test_pyinstaller_entry_calls_freeze_support_before_gui():
    """PyInstaller Analysis entry is run-activity-browser.py (pyinstaller.spec).

    Without freeze_support in that script's __main__ block, Windows Pool
    workers relaunch full Activity Browser instances.
    """
    source = ENTRY_SCRIPT.read_text(encoding="utf-8")
    assert "multiprocessing.freeze_support()" in source
    assert 'if __name__ == "__main__":' in source
    # Import and GUI start must come after freeze_support in the main block.
    main_block = source.split('if __name__ == "__main__":', 1)[1]
    freeze_at = main_block.index("freeze_support()")
    import_at = main_block.index("from activity_browser import run_activity_browser")
    run_at = main_block.index("run_activity_browser()")
    assert freeze_at < import_at < run_at


def test_run_activity_browser_calls_freeze_support(monkeypatch):
    """Console-script / alternate entries still divert frozen Windows workers."""
    calls = []

    monkeypatch.setattr(
        "multiprocessing.freeze_support",
        lambda: calls.append("freeze"),
    )

    import activity_browser.__main__ as ab_main_mod

    monkeypatch.setattr(
        ab_main_mod,
        "run_activity_browser",
        lambda: calls.append("run"),
    )

    activity_browser.run_activity_browser()
    assert calls == ["freeze", "run"]


def test_safe_unlink_cache_ignores_permission_error():
    from activity_browser.bwutils.metadata.loader import MDSLoader

    def _boom(*, missing_ok=False):
        raise PermissionError(32, "in use", "metadatastore_cache.pkl")

    cache_path = SimpleNamespace(unlink=_boom)
    MDSLoader._safe_unlink_cache(cache_path)
