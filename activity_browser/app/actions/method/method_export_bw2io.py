"""Export impact categories as bw2io LCIA files."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from qtpy import QtWidgets
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import app
from activity_browser.app import application
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.app.panes.impact_categories import resolve_methods_for_export
from activity_browser.bwutils.impact_categories import (
    CancelledError,
    method_name_to_filename_stem,
    raise_if_cancelled,
)
from activity_browser.bwutils.impact_categories.bw2io_lcia_file import (
    export_method_bw2io_xlsx,
    export_methods_bw2io_csv_batch,
)
from activity_browser.ui.core import threading
from activity_browser.app.dialogs import run_thread_with_progress


class MethodExportBW2IO(ABAction):
    icon = application.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton)
    text = "To bw2io LCIA file (.xlsx/.csv)…"
    tool_tip = "Export impact categories as bw2io LCIA files"

    @classmethod
    @exception_dialogs
    def run(cls, method_names: list[tuple] | None = None):
        method_names = resolve_methods_for_export(method_names)
        if not method_names:
            return

        fmt, ok = QtWidgets.QInputDialog.getItem(
            app.main_window,
            "bw2io export format",
            "Format:",
            ["Excel (.xlsx, one file per impact category)", "CSV (folder + metadata.csv)"],
            0,
            False,
        )
        if not ok:
            return

        directory = QtWidgets.QFileDialog.getExistingDirectory(
            app.main_window,
            "Select folder for bw2io Excel files"
            if fmt.startswith("Excel")
            else "Select folder for bw2io CSV files",
        )
        if not directory:
            return

        export_bw2io_with_progress(
            method_names, directory, as_excel=fmt.startswith("Excel")
        )


class ExportBW2IOThread(threading.ABThread):
    done: SignalInstance = Signal(str)
    failed: SignalInstance = Signal(str)

    method_names: list
    directory: str
    as_excel: bool

    def run_safely(self):
        try:
            directory = Path(self.directory)
            cancel = lambda: self.ab_cancel_requested()
            if self.as_excel:
                import tqdm

                for name in tqdm.tqdm(
                    self.method_names,
                    desc="Exporting bw2io Excel",
                    total=len(self.method_names),
                ):
                    raise_if_cancelled(cancel)
                    path = directory / f"{method_name_to_filename_stem(name)}.xlsx"
                    export_method_bw2io_xlsx(name, path)
                message = (
                    f"Wrote {len(self.method_names)} Excel file(s) to:\n{directory}"
                )
            else:
                written = export_methods_bw2io_csv_batch(
                    self.method_names, directory, cancel_check=cancel
                )
                message = f"Wrote {len(written)} file(s) to:\n{directory}"
        except CancelledError:
            self.request_ab_cancel()
            return
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        if self.ab_cancel_requested():
            return
        self.done.emit(message)


def export_bw2io_with_progress(
    method_names: Sequence[tuple],
    directory: str,
    *,
    as_excel: bool,
) -> None:
    thread = ExportBW2IOThread(app.application)
    thread.method_names = list(method_names)
    thread.directory = directory
    thread.as_excel = as_excel

    def done(message: str):
        QtWidgets.QMessageBox.information(app.main_window, "Export complete", message)

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
