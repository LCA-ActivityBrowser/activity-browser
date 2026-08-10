"""Source-level smoke checks for method import progress wiring (no app startup)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD = ROOT / "activity_browser" / "app" / "actions" / "method"
APP_DIALOGS = ROOT / "activity_browser" / "app" / "dialogs"


def test_method_import_ecoinvent_uses_ui_progress_dialog():
    src = (METHOD / "method_import_ecoinvent.py").read_text(encoding="utf-8")
    assert "from activity_browser.ui.dialogs import ABProgressDialog" in src
    assert "widgets.ABProgressDialog" not in src
    assert "composites" not in src


def test_method_file_actions_use_run_thread_with_progress():
    progress_src = (APP_DIALOGS / "thread_progress.py").read_text(encoding="utf-8")
    assert "def run_thread_with_progress(" in progress_src

    for name in (
        "method_import_ab.py",
        "method_import_bw2io.py",
        "method_export_ab.py",
        "method_export_bw2io.py",
    ):
        src = (METHOD / name).read_text(encoding="utf-8")
        assert "run_thread_with_progress" in src, name
        assert "from activity_browser.app.dialogs import run_thread_with_progress" in src, name
