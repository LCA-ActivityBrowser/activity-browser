# -*- coding: utf-8 -*-
"""Modal blocking operations for plugins."""
from __future__ import annotations

from typing import Any, Callable

from qtpy import QtCore, QtWidgets

from activity_browser.ui.core.threading import SafeBWConnection
from activity_browser.ui.dialogs import ABProgressDialog


class _PluginBlockingThread(QtCore.QThread):
    def __init__(self, func: Callable[[], Any], parent=None):
        super().__init__(parent)
        self._func = func
        self.error: BaseException | None = None
        self.result: Any = None

    def run(self) -> None:
        with SafeBWConnection():
            try:
                self.result = self._func()
            except BaseException as exc:
                self.error = exc


def run_blocking_operation(
    parent: QtWidgets.QWidget,
    title: str,
    func: Callable[[], Any],
    *,
    cancellable: bool = False,
) -> Any:
    """Run ``func`` on a worker thread behind a modal progress dialog."""
    dialog = ABProgressDialog.get_connected_dialog(title, cancellable=cancellable)
    dialog.setWindowTitle(title)
    dialog.setLabelText("Working…")
    dialog.setRange(0, 0)
    dialog.setModal(True)

    thread = _PluginBlockingThread(func, parent)

    def on_finished() -> None:
        dialog.detach()
        dialog.setMaximum(1)
        dialog.setValue(1)
        dialog.close()

    thread.finished.connect(on_finished)

    if cancellable:
        def on_cancel() -> None:
            thread.requestInterruption()

        dialog.canceled.connect(on_cancel)

    dialog.show()
    thread.start()

    loop = QtCore.QEventLoop()
    thread.finished.connect(loop.quit)
    loop.exec()

    if thread.error is not None:
        QtWidgets.QMessageBox.critical(
            parent,
            f"An error occurred: {type(thread.error).__name__}",
            str(thread.error),
        )
        raise thread.error
    return thread.result
