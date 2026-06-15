from uuid import uuid4

from qtpy import QtWidgets

import bw2data as bd

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.commontasks import get_writable_databases
from activity_browser.ui.icons import qicons


def _parse_categories(text: str) -> tuple[str, ...]:
    if not text or not text.strip():
        return ()
    return tuple(part.strip() for part in text.split(",") if part.strip())


class NewElementaryFlow(ABAction):
    """Create a new elementary flow in a writable database."""

    icon = qicons.add
    text = "New elementary flow"

    @staticmethod
    @exception_dialogs
    def run(
        database_name: str | None = None,
        *,
        link_to_process: tuple | None = None,
    ):
        writable = get_writable_databases()
        if not writable:
            QtWidgets.QMessageBox.warning(
                app.main_window,
                "No writable database",
                "No writable database is available. Unlock or create a database first.",
            )
            return

        default_db = next(
            (d for d in (database_name, bd.config.biosphere) if d in writable),
            writable[0],
        )
        dialog = NewElementaryFlowDialog(default_db, writable, app.main_window)
        if dialog.exec_() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        db_name, name, unit, flow_type, categories = dialog.get_data()
        if not name:
            return

        flow = bd.Database(db_name).new_activity(
            code=uuid4().hex,
            name=name,
            unit=unit,
            type=flow_type,
            categories=categories,
        )
        flow.save()

        if link_to_process is not None:
            from activity_browser.app.actions.exchange.exchange_new import ExchangeNew

            ExchangeNew.run([flow.key], link_to_process, "biosphere")


class NewElementaryFlowDialog(QtWidgets.QDialog):
    def __init__(
        self,
        default_database: str,
        databases: list[str],
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("New elementary flow")

        self._database_combo = QtWidgets.QComboBox()
        self._database_combo.addItems(databases)
        if default_database in databases:
            self._database_combo.setCurrentText(default_database)

        self._name_edit = QtWidgets.QLineEdit()
        self._unit_edit = QtWidgets.QLineEdit("kilogram")
        self._type_combo = QtWidgets.QComboBox()
        self._type_combo.addItems(["emission", "natural resource"])
        self._categories_edit = QtWidgets.QLineEdit()
        self._categories_edit.setPlaceholderText("e.g. air, non-urban")

        self._ok_button = QtWidgets.QPushButton("Create")
        self._ok_button.clicked.connect(self.accept)
        self._ok_button.setEnabled(False)
        self._cancel_button = QtWidgets.QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.reject)

        self._name_edit.textChanged.connect(
            lambda text: self._ok_button.setEnabled(bool(text.strip()))
        )

        layout = QtWidgets.QGridLayout()
        row = 0
        layout.addWidget(QtWidgets.QLabel("Database"), row, 0)
        layout.addWidget(self._database_combo, row, 1)
        row += 1
        layout.addWidget(QtWidgets.QLabel("Name"), row, 0)
        layout.addWidget(self._name_edit, row, 1)
        row += 1
        layout.addWidget(QtWidgets.QLabel("Unit"), row, 0)
        layout.addWidget(self._unit_edit, row, 1)
        row += 1
        layout.addWidget(QtWidgets.QLabel("Type"), row, 0)
        layout.addWidget(self._type_combo, row, 1)
        row += 1
        layout.addWidget(QtWidgets.QLabel("Categories"), row, 0)
        layout.addWidget(self._categories_edit, row, 1)
        row += 1
        layout.addWidget(self._ok_button, row, 0)
        layout.addWidget(self._cancel_button, row, 1)
        self.setLayout(layout)

    def get_data(self) -> tuple[str, str, str, str, tuple[str, ...]]:
        return (
            self._database_combo.currentText(),
            self._name_edit.text().strip(),
            self._unit_edit.text().strip() or "kilogram",
            self._type_combo.currentText(),
            _parse_categories(self._categories_edit.text()),
        )
