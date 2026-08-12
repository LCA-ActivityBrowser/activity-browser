"""Export impact categories to an AB LCIA file (.xlsx/.csv)."""
from __future__ import annotations

from typing import List, Optional, Sequence

from loguru import logger
from qtpy import QtWidgets
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import app
from activity_browser.app import application
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.app.panes.impact_categories import resolve_methods_for_export
from activity_browser.bwutils.impact_categories import (
    CancelledError,
    export_methods_ab_csv_pair,
    export_methods_ab_xlsx,
)
from activity_browser.ui.core import threading
from activity_browser.app.dialogs import run_thread_with_progress


class MethodExportAB(ABAction):
    """Export selected (or all) impact categories to an AB LCIA Excel workbook."""

    icon = application.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
    text = "To AB LCIA file (.xlsx/.csv)…"
    tool_tip = "Export impact categories to Activity Browser spreadsheet format"

    @classmethod
    @exception_dialogs
    def run(cls, method_names: Optional[List[tuple]] = None):
        method_names = resolve_methods_for_export(method_names)
        if not method_names:
            return

        path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=app.main_window,
            caption="Export impact categories (AB impact-category file)",
            directory="ab-impact-categories.xlsx",
            filter="Excel spreadsheet (*.xlsx);;CSV pair (*.cfs.csv);; All files (*.*)",
        )
        if not path:
            return

        as_csv = "CSV" in selected_filter or path.lower().endswith(".cfs.csv")
        if as_csv and path.lower().endswith(".xlsx"):
            path = path[:-5]
        elif not as_csv and not path.lower().endswith(".xlsx"):
            path = path + ".xlsx"

        export_ab_with_progress(method_names, path, as_csv=as_csv)


class ExportABThread(threading.ABThread):
    done: SignalInstance = Signal(str)
    failed: SignalInstance = Signal(str)

    method_names: list
    path: str
    as_csv: bool

    def run_safely(self):
        try:
            if self.ab_cancel_requested():
                return
            cancel = lambda: self.ab_cancel_requested()
            if self.as_csv:
                cfs_path, ic_path = export_methods_ab_csv_pair(
                    self.method_names, self.path, cancel_check=cancel
                )
                message = f"{cfs_path}\n{ic_path}"
            else:
                export_methods_ab_xlsx(
                    self.method_names, self.path, cancel_check=cancel
                )
                message = self.path
        except CancelledError:
            self.request_ab_cancel()
            return
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        if self.ab_cancel_requested():
            return
        self.done.emit(message)


def export_ab_with_progress(
    method_names: Sequence[tuple],
    path: str,
    *,
    as_csv: bool,
) -> None:
    thread = ExportABThread(app.application)
    thread.method_names = list(method_names)
    thread.path = path
    thread.as_csv = as_csv

    def done(message: str):
        logger.info(
            f"Exported {len(method_names)} impact categories to {message.replace(chr(10), ' and ')}"
        )
        QtWidgets.QMessageBox.information(
            app.main_window,
            "Export complete",
            f"Exported {len(method_names)} impact categories to:\n{message}",
        )

    def failed(message: str):
        QtWidgets.QMessageBox.warning(app.main_window, "Export impact categories", message)

    thread.done.connect(done)
    thread.failed.connect(failed)
    run_thread_with_progress(
        "Exporting impact categories",
        thread,
        on_cancelled=lambda: QtWidgets.QMessageBox.information(
            app.main_window, "Export cancelled", "Export cancelled."
        ),
    )
