"""Import impact categories from bw2io LCIA files."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.app.actions.method.method_import_ab import (
    MultiImportSetupDialog,
    finalize_lcia_import,
    notify_import_cancelled,
)
from activity_browser.bwutils.impact_categories import (
    ConflictMode,
    join_tuple_path,
    split_tuple_path,
)
from activity_browser.bwutils.impact_categories.bw2io_lcia_file import (
    load_bw2io_lcia_file,
    read_bw2io_metadata_csv,
    read_bw2io_metadata_xlsx,
)
from activity_browser.mod import bw2data as bd
from activity_browser.ui import widgets
from activity_browser.ui.core import threading
from activity_browser.app.dialogs import run_thread_with_progress
from activity_browser.ui.icons import qicons


class MethodImportBW2IO(ABAction):
    """Import one or more bw2io impact-category files."""

    icon = qicons.import_db
    text = "From bw2io LCIA file (.xlsx/.csv)…"
    tool_tip = "Import one or more bw2io LCIA Excel or CSV files"

    @classmethod
    @exception_dialogs
    def run(cls):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            parent=app.main_window,
            caption="Import bw2io LCIA file(s)",
            filter="LCIA (*.xlsx *.csv);;Excel (*.xlsx);;CSV (*.csv);;All files (*.*)",
        )
        if not paths:
            return

        path_objs = [Path(p) for p in paths]
        if len(path_objs) == 1:
            cls._import_single(path_objs[0])
        else:
            cls._import_many(path_objs)

    @classmethod
    def _import_single(cls, path: Path):
        prefill = _prefill_for_bw2io_path(path)
        dialog = BW2IOMetadataDialog(prefill, parent=app.main_window)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        name = split_tuple_path(dialog.method_path)
        if not name:
            QtWidgets.QMessageBox.warning(
                app.main_window,
                "Import bw2io LCIA",
                "Method name is required (use :: between parts).",
            )
            return

        overwrite = False
        if name in bd.methods:
            conflict = BW2IOLciaFileConflictDialog(name, parent=app.main_window)
            if conflict.exec_() != QtWidgets.QDialog.Accepted:
                return
            name = conflict.result_name
            overwrite = conflict.overwrite

        bio = BiospherePickDialog(parent=app.main_window)
        if bio.exec_() != QtWidgets.QDialog.Accepted:
            return

        def after_load(data: list):
            finalize_lcia_import(
                data,
                biosphere_name=bio.biosphere_name,
                overwrite=overwrite,
            )

        load_bw2io_file_with_progress(
            path,
            name=name,
            unit=dialog.unit,
            description=dialog.description,
            on_loaded=after_load,
        )

    @classmethod
    def _import_many(cls, paths: list[Path]):
        rows = []
        for path in paths:
            prefill = _prefill_for_bw2io_path(path)
            rows.append(
                {
                    "path": path,
                    "method": prefill.get("method") or "",
                    "unit": prefill.get("unit") or "",
                    "description": prefill.get("description") or "",
                }
            )

        review = BW2IOBatchMetadataDialog(rows, parent=app.main_window)
        if review.exec_() != QtWidgets.QDialog.Accepted:
            return

        def after_load(data: list):
            if not data:
                QtWidgets.QMessageBox.warning(
                    app.main_window,
                    "Import bw2io LCIA",
                    "No impact categories found in the selected files.",
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

        load_bw2io_files_with_progress(review.rows, on_loaded=after_load)


class BW2IOLciaFileConflictDialog(QtWidgets.QDialog):
    """Overwrite / edit name / cancel when a bw2io impact-category file name already exists."""

    result_name: tuple
    overwrite: bool

    def __init__(self, name: tuple, parent=None):
        super().__init__(parent)
        self._original = tuple(name)
        self.setWindowTitle("Impact category already exists")
        self.name_edit = QtWidgets.QLineEdit(join_tuple_path(name))
        info = QtWidgets.QLabel(
            f"<b>{join_tuple_path(name)}</b> already exists in this project."
        )
        info.setWordWrap(True)
        buttons = QtWidgets.QDialogButtonBox()
        self.overwrite_btn = buttons.addButton(
            "Overwrite", QtWidgets.QDialogButtonBox.AcceptRole
        )
        self.use_name_btn = buttons.addButton(
            "Use edited name", QtWidgets.QDialogButtonBox.AcceptRole
        )
        buttons.addButton(QtWidgets.QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.reject)
        self.overwrite_btn.clicked.connect(self._accept_overwrite)
        self.use_name_btn.clicked.connect(self._accept_edit)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(info)
        layout.addWidget(QtWidgets.QLabel("Name (:: parts):"))
        layout.addWidget(self.name_edit)
        layout.addWidget(buttons)

    def _accept_overwrite(self):
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Overwrite impact category",
            f"Overwrite {join_tuple_path(self._original)}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return
        self.result_name = self._original
        self.overwrite = True
        self.accept()

    def _accept_edit(self):
        name = split_tuple_path(self.name_edit.text().strip())
        if not name:
            QtWidgets.QMessageBox.warning(self, "Edit name", "Name cannot be empty.")
            return
        if name in bd.methods and name != self._original:
            QtWidgets.QMessageBox.warning(
                self,
                "Edit name",
                "That name already exists. Choose another or overwrite the original.",
            )
            return
        self.result_name = name
        self.overwrite = name == self._original and name in bd.methods
        if self.overwrite:
            self._accept_overwrite()
            return
        self.accept()


class BiospherePickDialog(QtWidgets.QDialog):
    biosphere_name: str

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose biosphere database")
        self.db_chooser = widgets.ABComboBox.get_database_combobox(self)
        default_bio = bd.config.biosphere
        idx = self.db_chooser.findText(default_bio)
        if idx >= 0:
            self.db_chooser.setCurrentIndex(idx)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.db_chooser)
        layout.addWidget(buttons)

    def accept(self):
        self.biosphere_name = self.db_chooser.currentText()
        super().accept()


class BW2IOMetadataDialog(QtWidgets.QDialog):
    method_path: str
    unit: str
    description: str

    def __init__(self, prefill: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("bw2io impact category metadata")
        self.method_edit = QtWidgets.QLineEdit(prefill.get("method") or "")
        self.method_edit.setPlaceholderText("My method::climate change::GWP100")
        self.unit_edit = QtWidgets.QLineEdit(prefill.get("unit") or "")
        self.description_edit = QtWidgets.QPlainTextEdit(
            prefill.get("description") or ""
        )
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QFormLayout(self)
        layout.addRow("Method (:: parts):", self.method_edit)
        layout.addRow("Unit:", self.unit_edit)
        layout.addRow("Description:", self.description_edit)
        layout.addRow(buttons)

    def accept(self):
        self.method_path = self.method_edit.text().strip()
        self.unit = self.unit_edit.text().strip()
        self.description = self.description_edit.toPlainText().strip()
        super().accept()


class BW2IOBatchMetadataDialog(QtWidgets.QDialog):
    """Edit method / unit / description for several bw2io impact-category files."""

    rows: list[dict]

    def __init__(self, rows: list[dict], parent=None):
        super().__init__(parent)
        self._rows = [dict(r) for r in rows]
        self.setWindowTitle("bw2io impact category metadata")
        self.resize(820, min(120 + 28 * len(rows), 520))

        self.table = QtWidgets.QTableWidget(len(rows), 4)
        self.table.setHorizontalHeaderLabels(
            ["File", "Method (:: parts)", "Unit", "Description"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        for i, row in enumerate(self._rows):
            file_item = QtWidgets.QTableWidgetItem(Path(row["path"]).name)
            file_item.setFlags(file_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(i, 0, file_item)
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(row.get("method") or ""))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(row.get("unit") or ""))
            self.table.setItem(
                i, 3, QtWidgets.QTableWidgetItem(row.get("description") or "")
            )

        info = QtWidgets.QLabel(
            f"Review metadata for <b>{len(rows)}</b> bw2io file(s). "
            "Method names use <code>::</code> between Brightway parts."
        )
        info.setWordWrap(True)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(info)
        layout.addWidget(self.table)
        layout.addWidget(buttons)

    def accept(self):
        seen: set[tuple] = set()
        out: list[dict] = []
        for i, row in enumerate(self._rows):
            method_text = (self.table.item(i, 1).text() or "").strip()
            name = split_tuple_path(method_text)
            if not name:
                QtWidgets.QMessageBox.warning(
                    self,
                    "bw2io metadata",
                    f"Row {i + 1} ({Path(row['path']).name}): method name is required.",
                )
                return
            if name in seen:
                QtWidgets.QMessageBox.warning(
                    self,
                    "bw2io metadata",
                    f"Duplicate method name in the selection:\n{join_tuple_path(name)}",
                )
                return
            seen.add(name)
            out.append(
                {
                    "path": row["path"],
                    "name": name,
                    "unit": (self.table.item(i, 2).text() or "").strip(),
                    "description": (self.table.item(i, 3).text() or "").strip(),
                }
            )
        self.rows = out
        super().accept()


def _prefill_for_bw2io_path(path: Path) -> dict[str, str]:
    prefill = {"method": "", "unit": "", "description": ""}
    if path.suffix.lower() in {".xlsx", ".xls"}:
        prefill.update(read_bw2io_metadata_xlsx(path) or {})
    else:
        sibling = path.with_name("metadata.csv")
        row = read_bw2io_metadata_csv(sibling, cf_filename=path.name)
        if row:
            prefill.update(row)
    return prefill


class LoadBW2IOFileThread(threading.ABThread):
    loaded: SignalInstance = Signal(object)
    failed: SignalInstance = Signal(str)

    path: Path
    name: tuple
    unit: str
    description: str

    def run_safely(self):
        try:
            if self.ab_cancel_requested():
                return
            data = load_bw2io_lcia_file(
                self.path,
                name=self.name,
                unit=self.unit,
                description=self.description,
            )
        except (ValueError, FileNotFoundError) as exc:
            self.failed.emit(str(exc))
            return
        if self.ab_cancel_requested():
            return
        self.loaded.emit(data)


class LoadBW2IOFilesThread(threading.ABThread):
    """Load several bw2io impact-category files into one importer-shaped list."""

    loaded: SignalInstance = Signal(object)
    failed: SignalInstance = Signal(str)

    specs: list

    def run_safely(self):
        import tqdm

        combined: list = []
        try:
            for spec in tqdm.tqdm(
                self.specs, desc="Loading bw2io files", total=len(self.specs)
            ):
                if self.ab_cancel_requested():
                    return
                combined.extend(
                    load_bw2io_lcia_file(
                        Path(spec["path"]),
                        name=tuple(spec["name"]),
                        unit=spec.get("unit") or "",
                        description=spec.get("description") or "",
                    )
                )
        except (ValueError, FileNotFoundError) as exc:
            self.failed.emit(str(exc))
            return
        if self.ab_cancel_requested():
            return
        self.loaded.emit(combined)


def load_bw2io_file_with_progress(
    path: Path,
    *,
    name: tuple,
    unit: str,
    description: str,
    on_loaded: Callable[[list], None],
) -> None:
    thread = LoadBW2IOFileThread(app.application)
    thread.path = path
    thread.name = name
    thread.unit = unit
    thread.description = description

    def _fail(message: str):
        QtWidgets.QMessageBox.warning(app.main_window, "Import bw2io LCIA", message)

    thread.failed.connect(_fail)
    thread.loaded.connect(on_loaded)
    run_thread_with_progress(
        "Loading impact category file",
        thread,
        on_cancelled=lambda: notify_import_cancelled("Import cancelled"),
    )


def load_bw2io_files_with_progress(
    specs: Sequence[dict],
    *,
    on_loaded: Callable[[list], None],
) -> None:
    thread = LoadBW2IOFilesThread(app.application)
    thread.specs = list(specs)

    def _fail(message: str):
        QtWidgets.QMessageBox.warning(app.main_window, "Import bw2io LCIA", message)

    thread.failed.connect(_fail)
    thread.loaded.connect(on_loaded)
    run_thread_with_progress(
        "Loading impact category files",
        thread,
        on_cancelled=lambda: notify_import_cancelled("Import cancelled"),
    )
