from uuid import uuid4

from qtpy import QtWidgets

import bw2data as bd

from bw_functional import Process

from activity_browser import application, bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ActivityNewProduct(ABAction):
    """
    ABAction to create a new activity. Prompts the user to supply a name. Returns if no name is supplied or if the user
    cancels. Otherwise, instructs the ActivityController to create a new activity.
    """

    icon = qicons.add
    text = "New product"

    @staticmethod
    @exception_dialogs
    def run(activities: list[tuple | int | bd.Node]):
        activities = [bwutils.refresh_node(activity) for activity in activities]

        for act in activities:
            assert isinstance(act, Process), "Cannot create new product for non-process type"
            # ask the user to provide a name for the new activity
            dialog = NewProductDialog(act, application.main_window)
            # if the user cancels, return
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                continue
            name, unit, location = dialog.get_new_process_data()
            # if no name is provided, return
            if not name:
                continue

            # create product
            new_prod_data = {
                "name": name,
                "unit": unit,
                "location": location,
                "type": "product",
            }
            new_product = act.new_product(code=uuid4().hex, **new_prod_data)
            new_product.save()


class NewProductDialog(QtWidgets.QDialog):
    """
    Gathers the paremeters for creating a new process.
    """

    def __init__(self, activity, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self.setWindowTitle("New product")

        self.name_edit = QtWidgets.QLineEdit()
        self.unit_edit = QtWidgets.QLineEdit("kilogram")
        self.location_edit = QtWidgets.QLineEdit(activity.get("location", ""))

        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setEnabled(False)

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        self.connect_signals()
        self.build_layout()

    def connect_signals(self):
        self.name_edit.textChanged.connect(lambda x: self.ok_button.setEnabled(bool(x)))

    def build_layout(self):
        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel("Product name"), 0, 0)
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QtWidgets.QLabel("Unit"), 1, 0)
        layout.addWidget(self.unit_edit, 1, 1)

        layout.addWidget(QtWidgets.QLabel("Location"), 2, 0)
        layout.addWidget(self.location_edit, 2, 1)

        layout.addWidget(self.ok_button, 3, 0)
        layout.addWidget(self.cancel_button, 3, 1)

        self.setLayout(layout)

    def get_new_process_data(self) -> tuple[str, str, str]:
        """Return the parameters the user entered."""
        return (
                self.name_edit.text(),
                self.unit_edit.text(),
                self.location_edit.text()
            )
