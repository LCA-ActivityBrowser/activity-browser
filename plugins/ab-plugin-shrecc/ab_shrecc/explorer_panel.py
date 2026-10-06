# -*- coding: utf-8 -*-
"""SHRECC Explorer tab: thin chrome + WebEngine embed."""
from __future__ import annotations

from typing import Callable

from qtpy import QtCore, QtGui, QtWidgets

from .explorer_session import ExplorerSession

try:
    from qtpy.QtWebEngineWidgets import QWebEngineView
except Exception:  # pragma: no cover
    QWebEngineView = None  # type: ignore


class PrepareWorker(QtCore.QThread):
    completed = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, session: ExplorerSession, parent=None):
        super().__init__(parent)
        self._session = session

    def run(self):
        try:
            self.completed.emit(self._session.run_prepare())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ExplorerPanel(QtWidgets.QWidget):
    def __init__(
        self,
        session: ExplorerSession,
        *,
        can_start_prepare: Callable[[], bool],
        begin_prepare: Callable[[], None],
        complete_prepare: Callable[[], None],
        fail_prepare: Callable[[], None],
        job_status_text: Callable[[], str],
        open_url: Callable[[str], None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._session = session
        self._can_start_prepare = can_start_prepare
        self._begin_prepare = begin_prepare
        self._complete_prepare = complete_prepare
        self._fail_prepare = fail_prepare
        self._job_status_text = job_status_text
        self._open_url = open_url or (
            lambda url: QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
        )
        self._worker: PrepareWorker | None = None

        root = QtWidgets.QVBoxLayout(self)
        chrome = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        chrome.addWidget(self.status_label, 1)
        self.prepare_btn = QtWidgets.QPushButton("Prepare")
        self.open_browser_btn = QtWidgets.QPushButton("Open in browser")
        chrome.addWidget(self.prepare_btn)
        chrome.addWidget(self.open_browser_btn)
        root.addLayout(chrome)

        self.error_label = QtWidgets.QLabel()
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        root.addWidget(self.error_label)

        self.stack = QtWidgets.QStackedWidget()
        self.empty_label = QtWidgets.QLabel()
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.stack.addWidget(self.empty_label)
        self.web = QWebEngineView() if QWebEngineView is not None else None
        if self.web is not None:
            self.stack.addWidget(self.web)
        else:
            fallback = QtWidgets.QLabel("Qt WebEngine unavailable; use Open in browser.")
            fallback.setAlignment(QtCore.Qt.AlignCenter)
            self.stack.addWidget(fallback)
        root.addWidget(self.stack, 1)

        self.prepare_btn.clicked.connect(self._on_prepare)
        self.open_browser_btn.clicked.connect(lambda: self._open_explorer(browser=True))
        self.refresh()

    def refresh(self) -> None:
        st = self._session.status()
        caption = f"Data directory: {st.data_dir}"
        self.status_label.setText(f"{st.message}\n{caption}" if st.message else caption)

        busy = self._worker is not None and self._worker.isRunning()
        if busy:
            self.prepare_btn.setText("Preparing…")
            self.prepare_btn.setEnabled(False)
        else:
            self.prepare_btn.setText("Refresh" if st.prepare_is_refresh else "Prepare")
            self.prepare_btn.setEnabled(st.can_prepare and self._can_start_prepare())
            if st.can_prepare and not self._can_start_prepare():
                self.prepare_btn.setToolTip(self._job_status_text())
            elif not st.can_prepare and st.can_embed:
                self.prepare_btn.setToolTip("Explorer data is up to date.")
            else:
                self.prepare_btn.setToolTip("")

        self.open_browser_btn.setEnabled(st.can_embed)
        if st.can_embed:
            self.stack.setCurrentIndex(1)
            self.empty_label.clear()
        else:
            self.stack.setCurrentIndex(0)
            self.empty_label.setText(st.message)
            self._session.stop_server()
            if self.web is not None:
                self.web.setUrl(QtCore.QUrl("about:blank"))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        if self._session.status().can_embed:
            self._open_explorer(browser=False)

    def shutdown(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(1000)
        self._session.stop_server()

    def _on_prepare(self) -> None:
        if not self._can_start_prepare() or not self._session.status().can_prepare:
            return
        self.error_label.hide()
        self._begin_prepare()
        self.prepare_btn.setEnabled(False)
        self.prepare_btn.setText("Preparing…")
        self._worker = PrepareWorker(self._session, parent=self)
        self._worker.completed.connect(self._on_prepare_done)
        self._worker.failed.connect(self._on_prepare_failed)
        self._worker.start()

    def _on_prepare_done(self, _written) -> None:
        self._complete_prepare()
        self._worker = None
        self.refresh()
        self._open_explorer(browser=False)

    def _on_prepare_failed(self, message: str) -> None:
        self._fail_prepare()
        self._worker = None
        self.error_label.setText(message)
        self.error_label.show()
        self.refresh()

    def _open_explorer(self, *, browser: bool) -> None:
        try:
            url = self._session.ensure_server()
        except RuntimeError as exc:
            self.error_label.setText(str(exc))
            self.error_label.show()
            return
        self.error_label.hide()
        if browser:
            self._open_url(url)
        if self.web is not None:
            self.web.setUrl(QtCore.QUrl(url))
            self.stack.setCurrentIndex(1)
