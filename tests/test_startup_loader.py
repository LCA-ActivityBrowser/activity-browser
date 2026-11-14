"""Startup loader failure handling (no second traceback / no main-window build)."""

import pytest
from PySide6 import QtWidgets


@pytest.fixture
def no_startup_dialogs(monkeypatch):
    """Keep startup failure tests non-blocking under offscreen Qt."""
    shown = []

    def _critical(parent, title, text, *args, **kwargs):
        shown.append((parent, title, text))
        return QtWidgets.QMessageBox.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", _critical)
    return shown


def test_module_thread_records_error_without_raising(qtbot, monkeypatch):
    from activity_browser.__main__ import ModuleThread

    thread = ModuleThread()
    monkeypatch.setattr(
        thread,
        "_load_modules",
        lambda: (_ for _ in ()).throw(ImportError("simulated missing dependency")),
    )

    with qtbot.waitSignal(thread.finished, timeout=5000):
        thread.start()

    assert isinstance(thread.error, ImportError)
    assert "simulated missing dependency" in str(thread.error)


def test_ab_loader_stops_on_module_thread_error(qtbot, monkeypatch, no_startup_dialogs):
    from activity_browser import __main__ as ab_main

    load_finished_calls = []
    quit_calls = []

    class FailingModuleThread(ab_main.ModuleThread):
        def run(self):
            self.error = RuntimeError("loader boom")

    monkeypatch.setattr(ab_main, "ModuleThread", FailingModuleThread)
    monkeypatch.setattr(
        ab_main.ABLoader,
        "load_finished",
        lambda self: load_finished_calls.append(True),
    )

    qapp = QtWidgets.QApplication.instance()
    monkeypatch.setattr(qapp, "quit", lambda: quit_calls.append(True))

    loader = ab_main.ABLoader()
    qtbot.addWidget(loader)

    qtbot.waitUntil(lambda: bool(no_startup_dialogs) or bool(quit_calls), timeout=5000)

    assert load_finished_calls == []
    assert len(no_startup_dialogs) == 1
    assert no_startup_dialogs[0][1] == "Activity Browser failed to start"
    assert "loader boom" in no_startup_dialogs[0][2]
    assert quit_calls == [True]
