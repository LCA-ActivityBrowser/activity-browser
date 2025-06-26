from qtpy import QtWidgets, QtCore

from activity_browser import application, bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from bw_functional import Process


class ProcessPropertyModify(ABAction):
    """
    Modify a property for all the products of a process.

    This method refreshes the given process, validates its type, and opens a dialog
    for the user to modify a property. If the property already exists, the dialog
    is pre-populated with its current values. The updated property is then applied
    to all products of the process.

    Args:
        process (tuple | int | Process): The process to modify. Can be a tuple, integer, or Process object.
        property_name (str, optional): The name of the property to modify. Defaults to None.

    Raises:
        ValueError: If the provided process is not of type Process.
    """

    icon = qicons.edit
    text = "Modify property"

    @staticmethod
    @exception_dialogs
    def run(process: tuple | int | Process,
            property_name: str = None
            ):

        process = bwutils.refresh_node(process)
        if not isinstance(process, Process):
            raise ValueError(f"Expected a Process-type activity, got {type(process)} instead")

        prop_dialog = PropertyDialog(process)

        # if the property already exists, populate the dialog with the existing values
        if property_name in process.available_properties():
            prop = process.property_template(property_name)
            prop_dialog.prop_name.setText(property_name)
            prop_dialog.prop_unit.setText(prop["unit"])
            prop_dialog.normalize_check.setChecked(prop.get("normalize", True))

        # show the dialog to the user
        if prop_dialog.exec_() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        name_changed = prop_dialog.name != property_name if property_name else False

        for product in process.products():
            # make sure the dictionaries are in place
            product["properties"] = product.get("properties", {})
            product["properties"][prop_dialog.name] = product["properties"].get(property_name, {})

            prop = {
                "unit": prop_dialog.prop["unit"],
                "normalize": prop_dialog.prop["normalize"],
                "amount": product["properties"][prop_dialog.name].get("amount", 1.0),
            }

            # update the property with the new values
            product["properties"][prop_dialog.name] = prop

            # if the name has changed, remove the old property
            if name_changed and property_name in product["properties"]:
                del product["properties"][property_name]

            product.save()


class PropertyDialog(QtWidgets.QDialog):
    name: str | None = None
    prop: dict | None = None

    def __init__(self, process: Process):
        super().__init__(application.main_window)
        self.process = process

        self.setWindowTitle("Add Property")

        self.prop_name = QtWidgets.QLineEdit(self)
        self.prop_name.setPlaceholderText("Property name")
        self.prop_name.textChanged.connect(self.validate)

        self.prop_unit = QtWidgets.QLineEdit(self)
        self.prop_unit.setPlaceholderText("Property unit")
        self.prop_unit.textChanged.connect(self.validate)

        self.normalize_label = QtWidgets.QLabel(" / amount", self)
        self.normalize_label.setVisible(False)
        self.normalize_check = QtWidgets.QCheckBox("per amount")
        self.normalize_check.toggled.connect(self.normalize_label.setVisible)
        self.normalize_check.toggled.connect(self.validate)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.prop_unit)
        h_layout.addWidget(self.normalize_label)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.prop_name)
        self.layout.addLayout(h_layout)
        self.layout.addWidget(self.normalize_check, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)

    def validate(self):
        if (
            self.prop_name.text() and
            self.prop_unit.text() and
            self.prop_name.text() not in self.process.get("properties", [])
        ):
            self.name = self.prop_name.text()
            self.prop = {
                "unit": self.prop_unit.text(),
                "normalize": self.normalize_check.isChecked(),
            }
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.name = None
            self.prop = None
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
