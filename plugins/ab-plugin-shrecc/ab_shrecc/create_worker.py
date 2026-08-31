# -*- coding: utf-8 -*-
"""Background SHRECC create worker thread."""
from __future__ import annotations

from typing import Any

from qtpy import QtCore

from .configure_model import background_database_names_from_kwargs
from .create_service import run_create
from .host_adapter import ShreccPluginHost


class CreateWorker(QtCore.QThread):
    completed = QtCore.Signal(object, dict)
    failed = QtCore.Signal(str)

    def __init__(
        self,
        kwargs: dict[str, Any],
        host: ShreccPluginHost,
        *,
        new_database_factory=None,
        parent=None,
    ):
        super().__init__(parent)
        self._kwargs = kwargs
        self._host = host
        self._new_database_factory = new_database_factory
        self._abandon = False

    def abandon(self) -> None:
        self._abandon = True

    def run(self) -> None:
        from activity_browser.ui.core.threading import SafeBWConnection

        names = background_database_names_from_kwargs(self._kwargs)
        try:
            with SafeBWConnection():
                with self._host.protect_databases(names):
                    if self._abandon:
                        return
                    ndb, result = run_create(
                        self._kwargs,
                        new_database_factory=self._new_database_factory,
                    )
                    if self._abandon:
                        return
                    self.completed.emit(ndb, result.artifacts)
        except BaseException as exc:
            if not self._abandon:
                self.failed.emit(str(exc))
