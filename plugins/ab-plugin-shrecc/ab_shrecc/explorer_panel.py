# -*- coding: utf-8 -*-
"""SHRECC Explorer tab: host chrome + optional WebEngine embed."""
from __future__ import annotations

from typing import Callable, Optional

from qtpy import QtCore, QtGui, QtWidgets

from .explorer_session import ExplorerSession

try:
    from qtpy.QtWebEngineWidgets import QWebEngineView
except Exception:  # pragma: no cover - optional at import time in some envs
    QWebEngineView = None  # type: ignore


class PrepareWorker(QtCore.QThread):
    completed = QtCore.Signal(object)  # list of paths
    failed = QtCore.Signal(str)

    def __init__(self, session: ExplorerSession, parent=None):
        super().__init__(parent)
        self._session = session

    def run(self):
        try:
            written = self._session.run_prepare()
            self.completed.emit(written)
        except Exception as exc:  # noqa: BLE001 — surface to chrome
            self.failed.emit(str(exc))


class ExplorerPanel(QtWidgets.QWidget):
    """Plugin-level Explorer: status chrome, Prepare, Open in browser, embed."""

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
        self._open_url = open_url or (lambda url: QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)))
        self._worker: PrepareWorker | None = None

        layout = QtWidgets.QVBoxLayout(self)

        chrome = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        chrome.addWidget(self.status_label, 1)
        self.prepare_btn = QtWidgets.QPushButton("Prepare")
        self.open_browser_btn = QtWidgets.QPushButton("Open in browser")
        chrome.addWidget(self.prepare_btn)
        chrome.addWidget(self.open_browser_btn)
        layout.addLayout(chrome)

        self.error_label = QtWidgets.QLabel()
        self.error_label.setStyleSheet("color: #b00020;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.stack = QtWidgets.QStackedWidget()
        self.empty_label = QtWidgets.QLabel()
        self.empty_label.setAlignment(QtCore.Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.stack.addWidget(self.empty_label)

        self.web = None
        if QWebEngineView is not None:
            self.web = QWebEngineView()
            self.stack.addWidget(self.web)
        else:
            self.web_fallback = QtWidgets.QLabel(
                "Qt WebEngine is unavailable; use Open in browser."
            )
            self.web_fallback.setAlignment(QtCore.Qt.AlignCenter)
            self.stack.addWidget(self.web_fallback)
        layout.addWidget(self.stack, 1)

        self.prepare_btn.clicked.connect(self._on_prepare)
        self.open_browser_btn.clicked.connect(self._on_open_browser)

        self.refresh()

    def refresh(self) -> None:
        status = self._session.status()
        self.status_label.setText(
            f"{status.message}\nData directory: {status.data_dir}"
        )
        prepare_ok = status.can_prepare and self._can_start_prepare()
        self.prepare_btn.setEnabled(prepare_ok)
        if not self._can_start_prepare() and status.can_prepare:
            self.prepare_btn.setToolTip(self._job_status_text())
        else:
            self.prepare_btn.setToolTip("Build explorer datasets from SHRECC cache.")
        self.open_browser_btn.setEnabled(status.can_embed)
        if status.can_embed:
            self.stack.setCurrentIndex(1)
            self.empty_label.setText("")
        else:
            self.stack.setCurrentIndex(0)
            self.empty_label.setText(status.message)
            self._session.stop_server()
            if self.web is not None:
                self.web.setUrl(QtCore.QUrl("about:blank"))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        status = self._session.status()
        if status.can_embed:
            self._try_embed()

    def shutdown(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(1000)
        self._session.stop_server()

    def _on_prepare(self) -> None:
        if not self._can_start_prepare():
            return
        if not self._session.status().can_prepare:
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
        self.prepare_btn.setText("Prepare")
        self.refresh()
        self._try_embed()

    def _on_prepare_failed(self, message: str) -> None:
        self._fail_prepare()
        self._worker = None
        self.prepare_btn.setText("Prepare")
        self.error_label.setText(message)
        self.error_label.show()
        self.refresh()

    def _on_open_browser(self) -> None:
        try:
            url = self._session.ensure_server()
        except RuntimeError as exc:
            self.error_label.setText(str(exc))
            self.error_label.show()
            return
        self.error_label.hide()
        self._open_url(url)
        self._load_web(url)

    def _try_embed(self) -> None:
        try:
            url = self._session.ensure_server()
        except RuntimeError as exc:
            self.error_label.setText(str(exc))
            self.error_label.show()
            return
        self.error_label.hide()
        self._load_web(url)

    def _load_web(self, url: str) -> None:
        if self.web is not None:
            self.web.setUrl(QtCore.QUrl(url))
            self.stack.setCurrentIndex(1)
