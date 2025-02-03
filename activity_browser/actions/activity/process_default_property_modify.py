from qtpy import QtWidgets, QtGui, QtCore

from activity_browser import application, bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from bw_functional import Process


class ProcessDefaultPropertyModify(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.edit
    text = "Modify property"

    @staticmethod
    @exception_dialogs
    def run(process: tuple | int | Process, property_name: str = None):
        process = bwutils.refresh_node(process)

        prop_dialog = DefaultPropertyDialog(process)

        if property_name in process.get("default_properties", {}):
            prop = process["default_properties"][property_name]
            prop_dialog.prop_name.setText(property_name)
            prop_dialog.prop_unit.setText(prop["unit"])
            prop_dialog.prop_value.setText(str(prop["amount"]))
            prop_dialog.normalize_check.setChecked(prop["normalize"])

        if prop_dialog.exec_() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        if property_name in process.get("default_properties", {}) and property_name == prop_dialog.name:
            process["default_properties"][property_name] = prop_dialog.prop
            process.save()

            for function in process.functions():
                function["properties"][property_name]["unit"] = prop_dialog.prop["unit"]
                function["properties"][property_name]["normalize"] = prop_dialog.prop["normalize"]
                function.save()

        elif property_name in process.get("default_properties", {}) and property_name != prop_dialog.name:
            del process["default_properties"][property_name]
            process["default_properties"][prop_dialog.name] = prop_dialog.prop
            process.save()

            for function in process.functions():
                function["properties"][prop_dialog.name] = {
                    "amount": function["properties"][property_name]["amount"],
                    "unit": prop_dialog.prop["unit"],
                    "normalize": prop_dialog.prop["normalize"],
                }
                del function["properties"][property_name]
                function.save()

        else:
            process.new_default_property(name=prop_dialog.name, **prop_dialog.prop)


class DefaultPropertyDialog(QtWidgets.QDialog):
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

        self.prop_value = QtWidgets.QLineEdit(self)
        self.prop_value.setPlaceholderText("Default amount")
        self.prop_value.setValidator(QtGui.QDoubleValidator())
        self.prop_value.textChanged.connect(self.validate)

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
        h_layout.addWidget(self.prop_value)
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
            self.prop_value.text() and
            self.prop_name.text() not in self.process.get("properties", [])
        ):
            self.name = self.prop_name.text()
            self.prop = {
                "unit": self.prop_unit.text(),
                "amount": float(self.prop_value.text().replace(',', '.')),
                "normalize": self.normalize_check.isChecked(),
            }
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.name = None
            self.prop = None
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
