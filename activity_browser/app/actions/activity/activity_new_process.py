from uuid import uuid4

from qtpy import QtWidgets
import bw2data as bd

from activity_browser import app
from activity_browser.bwutils.commontasks import database_is_legacy
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from .activity_open import ActivityOpen


class ActivityNewProcess(ABAction):
    """
    ABAction to create a new activity. Prompts the user to supply a name. Returns if no name is supplied or if the user
    cancels. Otherwise, instructs the ActivityController to create a new activity.
    """

    icon = qicons.add
    text = "New process"

    @staticmethod
    @exception_dialogs
    def run(database_name: str):
        # ask the user to provide a name for the new activity
        dialog = NewNodeDialog(app.main_window)
        # if the user cancels, return
        if dialog.exec_() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        name, ref_product, unit, location = dialog.get_new_process_data()
        # if no name is provided, return
        if not name:
            return
        if ref_product == "":
            ref_product = name

        database = bd.Database(database_name)
        legacy_backend = database_is_legacy(database_name)

        # create process
        new_proc_data = {
            "name": name,
            "location": location,
            "type": "process" if not legacy_backend else "processwithreferenceproduct",
        }

        if legacy_backend:
            new_proc_data["reference product"] = ref_product
            new_proc_data["unit"] = unit

        new_process: bd.Node = database.new_activity(code=uuid4().hex, **new_proc_data)
        new_process.save()

        if legacy_backend:
            new_process.new_exchange(
                input=new_process.key,
                type="production",
                amount=1.0,
            ).save()

        if not legacy_backend:
            # create reference product
            new_ref_prod_data = {
                "product": ref_product,
                "unit": unit,
                "location": location,
                "type": "product",
            }
            prod = new_process.new_product(code=uuid4().hex, **new_ref_prod_data)
            prod.save()

        ActivityOpen.run([new_process.key])


class NewNodeDialog(QtWidgets.QDialog):
    """
    Gathers the paremeters for creating a new process.
    """

    def __init__(self, process: bool = True, parent = None):
        super().__init__(parent)
        layout = QtWidgets.QGridLayout()
        row = 0
        if process:
            self.setWindowTitle("New process")
            layout.addWidget(QtWidgets.QLabel("Process name"), row, 0)
        else:
            self.setWindowTitle("New product")
            layout.addWidget(QtWidgets.QLabel("Product name"), row, 0)
        self._process_name_edit = QtWidgets.QLineEdit()
        self._process_name_edit.textChanged.connect(self._handle_text_changed)
        layout.addWidget(self._process_name_edit, row, 1)
        row += 1
        self._ref_product_name_edit = QtWidgets.QLineEdit()
        if process:
            layout.addWidget(QtWidgets.QLabel("Product name"), row, 0)
            layout.addWidget(self._ref_product_name_edit, row, 1)
            row += 1
        layout.addWidget(QtWidgets.QLabel("Unit"), row, 0)
        self._unit_edit = QtWidgets.QLineEdit("kilogram")
        layout.addWidget(self._unit_edit, row, 1)
        row += 1
        layout.addWidget(QtWidgets.QLabel("Location"), row, 0)
        default_loc = "GLO" if process else ""
        self._location_edit = QtWidgets.QLineEdit(default_loc)
        layout.addWidget(self._location_edit, row, 1)
        row += 1
        self._ok_button = QtWidgets.QPushButton("OK")
        self._ok_button.clicked.connect(self.accept)
        self._ok_button.setEnabled(False)
        layout.addWidget(self._ok_button, row, 0)
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button, row, 1)
        self.setLayout(layout)

    def _handle_text_changed(self, text: str):
        self._ok_button.setEnabled(text != "")
        self._ref_product_name_edit.setPlaceholderText(text)

    def get_new_process_data(self) -> tuple[str, str, str, str]:
        """Return the parameters the user entered."""
        return (
                self._process_name_edit.text(),
                self._ref_product_name_edit.text(),
                self._unit_edit.text(),
                self._location_edit.text()
            )

