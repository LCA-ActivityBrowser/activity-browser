from qtpy import QtWidgets

import bw2data as bd

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.commontasks import biosphere_node_types, get_writable_databases
from activity_browser.bwutils.elementary_flows import create_elementary_flow
from activity_browser.ui.icons import qicons


def _parse_categories(text: str) -> tuple[str, ...]:
    if not text or not text.strip():
        return ()
    return tuple(part.strip() for part in text.split(",") if part.strip())


def _format_categories(categories) -> str:
    if not categories:
        return ""
    return ", ".join(str(part) for part in categories)


class NewElementaryFlow(ABAction):
    """Create a new elementary flow (biosphere node) in a writable database."""

    icon = qicons.add
    text = "New elementary flow"

    @staticmethod
    @exception_dialogs
    def run(database_name: str | None = None):
        """Prompt for flow metadata and save a new emission or resource flow."""
        writable = get_writable_databases()
        if not writable:
            QtWidgets.QMessageBox.warning(
                app.main_window,
                "No writable database",
                "No writable database is available. Unlock or create a database first.",
            )
            return

        db_name = database_name
        if db_name not in writable:
            if db_name:
                QtWidgets.QMessageBox.warning(
                    app.main_window,
                    "Database is read-only",
                    f"Cannot create elementary flows in read-only or locked database: {db_name}",
                )
                return
            db_name = next(
                (d for d in (bd.config.biosphere,) if d in writable),
                writable[0],
            )

        dialog = ElementaryFlowDialog(app.main_window)
        if dialog.exec_() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        name, unit, flow_type, categories = dialog.get_data()
        if not name:
            return

        create_elementary_flow(
            db_name,
            name=name,
            unit=unit,
            flow_type=flow_type,
            categories=categories,
        )


class ElementaryFlowDialog(QtWidgets.QDialog):
    """Dialog for name, unit, type, and categories of an elementary flow."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        *,
        flow: bd.Node | None = None,
    ):
        super().__init__(parent)
        self._edit_mode = flow is not None
        self.setWindowTitle("Edit elementary flow" if self._edit_mode else "New elementary flow")

        self._name_edit = QtWidgets.QLineEdit()
        self._unit_edit = QtWidgets.QLineEdit("kilogram")
        self._type_combo = QtWidgets.QComboBox()
        type_options = (
            sorted(biosphere_node_types())
            if self._edit_mode
            else ["emission", "natural resource"]
        )
        self._type_combo.addItems(type_options)
        self._categories_edit = QtWidgets.QLineEdit()
        self._categories_edit.setPlaceholderText("e.g. air, non-urban")

        if self._edit_mode:
            self._name_edit.setText(flow.get("name", ""))
            self._unit_edit.setText(flow.get("unit", "kilogram"))
            flow_type = flow.get("type", "")
            if flow_type and self._type_combo.findText(flow_type) < 0:
                self._type_combo.addItem(flow_type)
            if flow_type:
                self._type_combo.setCurrentText(flow_type)
            self._categories_edit.setText(_format_categories(flow.get("categories", ())))

        self._ok_button = QtWidgets.QPushButton("Save" if self._edit_mode else "Create")
        self._ok_button.clicked.connect(self.accept)
        self._ok_button.setEnabled(self._edit_mode and bool(self._name_edit.text().strip()))
        self._cancel_button = QtWidgets.QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.reject)

        self._name_edit.textChanged.connect(
            lambda text: self._ok_button.setEnabled(bool(text.strip()))
        )

        layout = QtWidgets.QGridLayout()
        row = 0
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

    def get_data(self) -> tuple[str, str, str, tuple[str, ...]]:
        return (
            self._name_edit.text().strip(),
            self._unit_edit.text().strip() or "kilogram",
            self._type_combo.currentText(),
            _parse_categories(self._categories_edit.text()),
        )
