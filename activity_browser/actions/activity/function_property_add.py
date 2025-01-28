import bw2data as bd

from qtpy import QtWidgets, QtGui, QtCore

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from bw_functional import Function


class FunctionPropertyAdd(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.right
    text = "Add property"

    @staticmethod
    @exception_dialogs
    def run(function: tuple | int | Function, property_name: str = None):
        if not isinstance(function, Function):
            if isinstance(function, tuple):
                function = bd.get_node(key=function)
            elif isinstance(function, int):
                function = bd.get_node(id=function)
            else:
                raise ValueError("Function must be either a tuple, int or Function instance")

        prop_dialog = AddPropertyDialog(function, property_name)
        if prop_dialog.exec_() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        props = function.get('properties', {})
        props.update(prop_dialog.data)
        function['properties'] = props
        function.save()


class AddPropertyDialog(QtWidgets.QDialog):
    data: dict

    def __init__(self, function: Function, property_name: str = None):
        super().__init__(application.main_window)
        self.function = function

        self.setWindowTitle("Add Property")

        self.prop_name = QtWidgets.QLineEdit(self)
        self.prop_name.setPlaceholderText("Property name")
        self.prop_name.setText(property_name)
        self.prop_name.textChanged.connect(self.validate)

        self.prop_unit = QtWidgets.QLineEdit(self)
        self.prop_unit.setPlaceholderText("Property unit")
        self.prop_unit.textChanged.connect(self.validate)

        self.prop_value = QtWidgets.QLineEdit(self)
        self.prop_value.setPlaceholderText("Property value")
        self.prop_value.setValidator(QtGui.QDoubleValidator())
        self.prop_value.textChanged.connect(self.validate)

        self.normalize_label = QtWidgets.QLabel(f" / {function["unit"]}", self)
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
            self.prop_name.text() not in self.function.get("properties", [])
        ):
            self.data = {
                self.prop_name.text(): {
                    "unit": self.prop_unit.text(),
                    "amount": float(self.prop_value.text().replace(',', '.')),
                    "normalize": self.normalize_check.isChecked(),
                }
            }
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.data = {}
            self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
