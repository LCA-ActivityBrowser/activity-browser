"""Startup loader failure handling (no second traceback / no main-window build)."""

import pytest
from PySide6 import QtWidgets


@pytest.fixture
def no_startup_dialogs(monkeypatch):
    """Keep startup failure tests non-blocking under offscreen Qt."""
    from activity_browser.__main__ import STARTUP_FAILURE_TITLE

    shown = []

    def _show(exc, parent=None):
        shown.append((parent, STARTUP_FAILURE_TITLE, str(exc)))

    monkeypatch.setattr(
        "activity_browser.__main__.show_startup_failure", _show
    )
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
    assert no_startup_dialogs[0][1] == ab_main.STARTUP_FAILURE_TITLE
    assert "loader boom" in no_startup_dialogs[0][2]
    assert quit_calls == [True]


def test_show_startup_failure_exposes_copyable_traceback(monkeypatch, capsys):
    """Users must be able to copy the traceback (details + stderr), not only a label."""
    from activity_browser import __main__ as ab_main

    recorded = {}

    class FakeSignal:
        def __init__(self):
            self._slots = []

        def connect(self, slot):
            self._slots.append(slot)

        def emit(self):
            for slot in self._slots:
                slot()

    class FakeButton:
        def __init__(self):
            self.clicked = FakeSignal()

    class FakeMessageBox:
        Critical = QtWidgets.QMessageBox.Critical
        Ok = QtWidgets.QMessageBox.Ok
        ActionRole = QtWidgets.QMessageBox.ActionRole

        def __init__(self, parent=None):
            self._parent = parent
            self._clicked = None
            self._closed = False
            recorded["box"] = self

        def setIcon(self, icon):
            recorded["icon"] = icon

        def setWindowTitle(self, title):
            recorded["title"] = title

        def setText(self, text):
            recorded["text"] = text

        def setDetailedText(self, text):
            recorded["detailed"] = text

        def addButton(self, *args):
            btn = FakeButton()
            recorded.setdefault("buttons", []).append((args, btn))
            if args and args[0] == "Copy details":
                recorded["copy_btn"] = btn
            else:
                recorded["ok_btn"] = btn
            return btn

        def clickedButton(self):
            return self._clicked

        def done(self, result):
            self._closed = True
            recorded["done_result"] = result

        def exec_(self):
            # Simulate Copy details (must not close), then Ok (closes).
            copy_btn = recorded["copy_btn"]
            self._clicked = copy_btn
            copy_btn.clicked.emit()
            type(self).done(self, 0)
            assert self._closed is False

            ok_btn = recorded["ok_btn"]
            self._clicked = ok_btn
            type(self).done(self, QtWidgets.QMessageBox.Ok)
            assert self._closed is True
            return QtWidgets.QMessageBox.Ok

    clipboard = {"text": None}

    class FakeClipboard:
        def setText(self, text):
            clipboard["text"] = text

    qapp = QtWidgets.QApplication.instance()
    monkeypatch.setattr(ab_main.QtWidgets, "QMessageBox", FakeMessageBox)
    monkeypatch.setattr(qapp, "clipboard", lambda: FakeClipboard())

    try:
        raise TypeError("got an unexpected keyword argument 'dataset'")
    except TypeError as exc:
        ab_main.show_startup_failure(exc)

    assert recorded["title"] == ab_main.STARTUP_FAILURE_TITLE
    assert "unexpected keyword argument 'dataset'" in recorded["text"]
    assert "Show Details" in recorded["text"] or "Copy details" in recorded["text"]
    assert "TypeError" in recorded["detailed"]
    assert "unexpected keyword argument 'dataset'" in recorded["detailed"]
    assert "Traceback" in recorded["detailed"]
    assert any(args and args[0] == "Copy details" for args, _ in recorded["buttons"])

    err = capsys.readouterr().err
    assert "TypeError" in err
    assert "unexpected keyword argument 'dataset'" in err
    assert clipboard["text"] == recorded["detailed"]
