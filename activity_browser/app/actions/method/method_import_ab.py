"""Import impact categories from an AB LCIA file (.xlsx/.csv)."""
from __future__ import annotations

import csv
from enum import Enum
from typing import Callable, Optional

from loguru import logger
from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.impact_categories import (
    ABLCIAImporter,
    CancelledError,
    ConflictMode,
    ab_csv_sibling_path,
    apply_name_conflicts,
    drop_unlinked_exchanges,
    exchange_link_counts,
    join_tuple_path,
    load_ab_csv_pair,
    load_ab_xlsx,
    split_tuple_path,
    unlinked_exchanges,
)
from activity_browser.mod import bw2data as bd
from activity_browser.ui import widgets
from activity_browser.ui.core import threading
from activity_browser.app.dialogs import run_thread_with_progress
from activity_browser.ui.icons import qicons


class MethodImportAB(ABAction):
    """Import impact categories from an AB LCIA Excel workbook or CSV pair."""

    icon = qicons.import_db
    text = "From AB LCIA file (.xlsx/.csv)…"
    tool_tip = "Import impact categories from Activity Browser spreadsheet format"

    @classmethod
    @exception_dialogs
    def run(cls):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=app.main_window,
            caption="Import impact categories (AB impact-category file)",
            filter=(
                "AB LCIA (*.xlsx *.cfs.csv *.metadata.csv);;"
                "Excel spreadsheet (*.xlsx);;"
                "AB CSV (*.cfs.csv *.metadata.csv);;"
                "All files (*.*)"
            ),
        )
        if not path:
            return

        other = None
        if not path.lower().endswith(".xlsx"):
            sibling = ab_csv_sibling_path(path)
            if sibling is None or not sibling.is_file():
                other, _ = QtWidgets.QFileDialog.getOpenFileName(
                    parent=app.main_window,
                    caption="Select matching AB CSV sibling file",
                    filter="AB CSV (*.cfs.csv *.metadata.csv);; All files (*.*)",
                )
                if not other:
                    return

        def after_load(data: list):
            if not data:
                QtWidgets.QMessageBox.warning(
                    app.main_window,
                    "Import impact categories",
                    "No impact categories found in the selected file.",
                )
                return

            setup = MultiImportSetupDialog(data, parent=app.main_window)
            if setup.exec_() != QtWidgets.QDialog.Accepted:
                return

            finalize_lcia_import(
                setup.prepared_data,
                biosphere_name=setup.biosphere_name,
                overwrite=setup.conflict_mode == ConflictMode.OVERWRITE,
            )

        load_ab_file_with_progress(path, other_path=other, on_loaded=after_load)


class UnlinkedDecision(str, Enum):
    CANCEL = "cancel"
    EXPORT = "export"
    DROP = "drop"
    CONTINUE = "continue"


def export_unmatched_cfs(unmatched: list[dict], parent=None) -> None:
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent or app.main_window,
        "Export unmatched characterization factors",
        "unmatched-cfs.csv",
        "CSV (*.csv);; All files (*.*)",
    )
    if not path:
        return
    if not path.lower().endswith(".csv"):
        path = path + ".csv"
    fieldnames = ["method", "name", "categories", "amount"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in unmatched:
            writer.writerow(
                {
                    "method": "::".join(map(str, row.get("method", ()))),
                    "name": row.get("name", ""),
                    "categories": "::".join(map(str, row.get("categories", ()))),
                    "amount": row.get("amount", ""),
                }
            )
    QtWidgets.QMessageBox.information(
        parent or app.main_window,
        "Unmatched CFs exported",
        f"Wrote {len(unmatched)} rows to:\n{path}",
    )


def ask_unlinked_cfs(linked: int, unlinked: int, parent=None) -> UnlinkedDecision:
    box = QtWidgets.QMessageBox(parent or app.main_window)
    box.setWindowTitle("Characterization factor linking")
    box.setIcon(QtWidgets.QMessageBox.Warning)
    box.setText(f"Linked: {linked}  |  Unlinked: {unlinked}")
    box.setInformativeText(
        "Cancel import, export the unmatched list, or drop unlinked CFs and continue?"
    )
    cancel = box.addButton("Cancel", QtWidgets.QMessageBox.RejectRole)
    export_btn = box.addButton("Export unmatched…", QtWidgets.QMessageBox.ActionRole)
    drop = box.addButton("Drop unlinked", QtWidgets.QMessageBox.DestructiveRole)
    box.setDefaultButton(cancel)
    box.exec_()
    clicked = box.clickedButton()
    if clicked is export_btn:
        return UnlinkedDecision.EXPORT
    if clicked is drop:
        confirm = QtWidgets.QMessageBox.question(
            parent or app.main_window,
            "Drop unlinked CFs",
            "Drop all unlinked characterization factors and write the rest?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return (
            UnlinkedDecision.DROP
            if confirm == QtWidgets.QMessageBox.Yes
            else UnlinkedDecision.CANCEL
        )
    return UnlinkedDecision.CANCEL


class MultiImportSetupDialog(QtWidgets.QDialog):
    """Biosphere + conflict policy for multi–impact-category imports."""

    biosphere_name: str
    conflict_mode: ConflictMode
    prepared_data: list

    def __init__(self, data: list[dict], parent=None):
        super().__init__(parent)
        self._data = data
        self.setWindowTitle("Import impact categories")

        self.db_chooser = widgets.ABComboBox.get_database_combobox(self)
        default_bio = bd.config.biosphere
        idx = self.db_chooser.findText(default_bio)
        if idx >= 0:
            self.db_chooser.setCurrentIndex(idx)

        self.conflict_skip = QtWidgets.QRadioButton("Skip existing impact categories")
        self.conflict_overwrite = QtWidgets.QRadioButton("Overwrite existing")
        self.conflict_rename = QtWidgets.QRadioButton("Rename conflicts with prefix")
        self.conflict_skip.setChecked(True)
        self.prefix_edit = QtWidgets.QLineEdit()
        self.prefix_edit.setPlaceholderText("Namespace prefix (e.g. Import 2026)")
        self.prefix_edit.setEnabled(False)
        self.conflict_rename.toggled.connect(self.prefix_edit.setEnabled)

        existing = set(bd.methods)
        conflicts = [ds for ds in data if tuple(ds["name"]) in existing]
        self._conflict_table: Optional[QtWidgets.QTableWidget] = None
        if conflicts:
            self._conflict_table = QtWidgets.QTableWidget(len(conflicts), 2)
            self._conflict_table.setHorizontalHeaderLabels(
                ["Existing name", "Import as (:: editable)"]
            )
            self._conflict_table.horizontalHeader().setStretchLastSection(True)
            for row, ds in enumerate(conflicts):
                original = join_tuple_path(ds["name"])
                item0 = QtWidgets.QTableWidgetItem(original)
                item0.setFlags(item0.flags() & ~QtCore.Qt.ItemIsEditable)
                item0.setData(QtCore.Qt.UserRole, tuple(ds["name"]))
                self._conflict_table.setItem(row, 0, item0)
                self._conflict_table.setItem(
                    row, 1, QtWidgets.QTableWidgetItem(original)
                )

        info = QtWidgets.QLabel(
            f"File contains <b>{len(data)}</b> impact categories"
            + (f" (<b>{len(conflicts)}</b> name conflicts)." if conflicts else ".")
        )
        info.setWordWrap(True)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(info)
        layout.addWidget(QtWidgets.QLabel("Biosphere database:"))
        layout.addWidget(self.db_chooser)
        layout.addWidget(QtWidgets.QLabel("If names already exist:"))
        layout.addWidget(self.conflict_skip)
        layout.addWidget(self.conflict_overwrite)
        layout.addWidget(self.conflict_rename)
        layout.addWidget(self.prefix_edit)
        if self._conflict_table is not None:
            layout.addWidget(
                QtWidgets.QLabel(
                    "Per-conflict rename (optional; overrides bulk policy for edited rows):"
                )
            )
            layout.addWidget(self._conflict_table)
        layout.addWidget(buttons)

    def _table_renames(self) -> dict[tuple, tuple]:
        renames: dict[tuple, tuple] = {}
        if self._conflict_table is None:
            return renames
        for row in range(self._conflict_table.rowCount()):
            original = self._conflict_table.item(row, 0).data(QtCore.Qt.UserRole)
            target_text = (self._conflict_table.item(row, 1).text() or "").strip()
            target = split_tuple_path(target_text)
            if target and target != original:
                renames[tuple(original)] = target
        return renames

    def accept(self):
        if self.conflict_overwrite.isChecked():
            confirm = QtWidgets.QMessageBox.question(
                self,
                "Overwrite impact categories",
                "Overwrite all conflicting impact categories?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
            mode = ConflictMode.OVERWRITE
            prefix = None
        elif self.conflict_rename.isChecked():
            mode = ConflictMode.RENAME_PREFIX
            prefix = self.prefix_edit.text().strip()
            if not prefix:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Rename conflicts",
                    "Please enter a namespace prefix.",
                )
                return
        else:
            mode = ConflictMode.SKIP
            prefix = None

        self.biosphere_name = self.db_chooser.currentText()
        self.conflict_mode = mode
        self.prepared_data = apply_name_conflicts(
            self._data,
            set(bd.methods),
            mode=mode,
            prefix=prefix,
            renames=self._table_renames(),
        )
        if not self.prepared_data:
            QtWidgets.QMessageBox.information(
                self,
                "Import impact categories",
                "Nothing left to import after applying the conflict policy.",
            )
            return
        super().accept()


def _cancel_check(thread: threading.ABThread) -> bool:
    return thread.ab_cancel_requested()


def notify_import_cancelled(title: str = "Cancelled") -> None:
    QtWidgets.QMessageBox.information(
        app.main_window,
        title,
        "Operation cancelled. No impact categories were written to the project.",
    )


class LoadABFileThread(threading.ABThread):
    loaded: SignalInstance = Signal(object)
    failed: SignalInstance = Signal(str)

    path: str
    other_path: Optional[str] = None

    def run_safely(self):
        path = self.path
        try:
            if self.ab_cancel_requested():
                return
            if path.lower().endswith(".xlsx"):
                data = load_ab_xlsx(path)
            else:
                data = load_ab_csv_pair(path, other_path=self.other_path)
        except (ValueError, FileNotFoundError) as exc:
            self.failed.emit(str(exc))
            return
        if self.ab_cancel_requested():
            return
        self.loaded.emit(data)


class LinkLCIAThread(threading.ABThread):
    linked: SignalInstance = Signal(object)

    data: list
    biosphere_name: str

    def run_safely(self):
        try:
            importer = ABLCIAImporter(self.data, biosphere=self.biosphere_name)
            importer.apply_strategies(cancel_check=lambda: _cancel_check(self))
        except CancelledError:
            self.request_ab_cancel()
            return
        if self.ab_cancel_requested():
            return
        self.linked.emit(importer)


class WriteLCIAThread(threading.ABThread):
    written: SignalInstance = Signal(int)
    failed: SignalInstance = Signal(str)

    importer: ABLCIAImporter
    overwrite: bool
    biosphere_name: str

    def run_safely(self):
        try:
            self.importer.write_methods(
                overwrite=self.overwrite,
                verbose=False,
                cancel_check=lambda: _cancel_check(self),
            )
        except CancelledError:
            self.request_ab_cancel()
            return
        except ValueError as exc:
            self.failed.emit(str(exc))
            return
        if self.ab_cancel_requested():
            return
        logger.info(
            f"Imported {len(self.importer.data)} impact categories "
            f"(biosphere={self.biosphere_name})"
        )
        self.written.emit(len(self.importer.data))


def load_ab_file_with_progress(
    path: str,
    *,
    other_path: Optional[str] = None,
    on_loaded: Callable[[list], None],
) -> None:
    thread = LoadABFileThread(app.application)
    thread.path = path
    thread.other_path = other_path

    def _fail(message: str):
        QtWidgets.QMessageBox.warning(
            app.main_window, "Import impact categories", message
        )

    thread.failed.connect(_fail)
    thread.loaded.connect(on_loaded)
    run_thread_with_progress(
        "Loading impact categories",
        thread,
        on_cancelled=lambda: notify_import_cancelled("Import cancelled"),
    )


def finalize_lcia_import(
    data: list[dict],
    *,
    biosphere_name: str,
    overwrite: bool,
    parent=None,
) -> None:
    """Apply strategies (with progress), gate on unlinked CFs, then write."""
    parent = parent or app.main_window
    link_thread = LinkLCIAThread(app.application)
    link_thread.data = data
    link_thread.biosphere_name = biosphere_name

    def after_link(importer: ABLCIAImporter):
        linked, unlinked = exchange_link_counts(importer.data)
        unmatched = unlinked_exchanges(importer.data)

        if unlinked:
            decision = ask_unlinked_cfs(linked, unlinked, parent=parent)
            if decision == UnlinkedDecision.CANCEL:
                return
            if decision == UnlinkedDecision.EXPORT:
                export_unmatched_cfs(unmatched, parent=parent)
                return
            if decision == UnlinkedDecision.DROP:
                importer.data = drop_unlinked_exchanges(importer.data)
        else:
            QtWidgets.QMessageBox.information(
                parent,
                "Ready to import",
                f"Linked: {linked}  |  Unlinked: 0\n\n"
                f"Writing {len(importer.data)} impact categories.",
            )

        write_thread = WriteLCIAThread(app.application)
        write_thread.importer = importer
        write_thread.overwrite = overwrite
        write_thread.biosphere_name = biosphere_name

        def after_write(count: int):
            QtWidgets.QMessageBox.information(
                parent,
                "Import complete",
                f"Imported {count} impact categories.",
            )

        def write_failed(message: str):
            QtWidgets.QMessageBox.warning(parent, "Import impact categories", message)

        write_thread.written.connect(after_write)
        write_thread.failed.connect(write_failed)

        def write_cancelled():
            if overwrite:
                QtWidgets.QMessageBox.information(
                    parent,
                    "Import cancelled",
                    "Import cancelled. Newly created impact categories from this run "
                    "were removed. Any categories already overwritten may remain updated.",
                )
            else:
                notify_import_cancelled("Import cancelled")

        run_thread_with_progress(
            "Writing impact categories",
            write_thread,
            on_cancelled=write_cancelled,
        )

    link_thread.linked.connect(after_link)
    run_thread_with_progress(
        "Linking characterization factors",
        link_thread,
        on_cancelled=lambda: notify_import_cancelled("Import cancelled"),
    )
