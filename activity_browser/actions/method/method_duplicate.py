from typing import List
from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class MethodDuplicate(ABAction):
    """
    ABAction to duplicate a method, or node with all underlying methods to a new name specified by the user.
    """

    icon = qicons.copy
    text = "Duplicate Impact Category"

    @staticmethod
    @exception_dialogs
    def run(methods: List[tuple], level: str):
        # this action can handle only one selected method for now
        selected_method = methods[0]

        # check whether we're dealing with a leaf or node. If it's a node, select all underlying methods for duplication
        if level is not None and level != "leaf":
            all_methods = [
                bd.Method(method)
                for method in bd.methods
                if set(selected_method).issubset(method)
            ]
        else:
            all_methods = [bd.Method(selected_method)]

        # retrieve the new name(s) from the user and return if canceled
        dialog = TupleNameDialog.get_combined_name(
            application.main_window,
            "Impact category name",
            "Combined name:",
            selected_method,
            " - Copy",
        )
        if dialog.exec_() != TupleNameDialog.Accepted:
            return

        # for each method to be duplicated, construct a new location
        location = dialog.result_tuple
        new_names = [location + method.name[len(location) :] for method in all_methods]

        # instruct the ImpactCategoryController to duplicate the methods to the new locations
        for method, new_name in zip(all_methods, new_names):
            if new_name in methods:
                raise Exception("New method name already in use")
            method.copy(new_name)
            log.info(f"Copied method {method.name} into {new_name}")


class TupleNameDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name_label = QtWidgets.QLabel("New name")
        self.view_name = QtWidgets.QLabel()

        self.input_fields = []
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.name_label)
        row.addWidget(self.view_name)
        layout.addLayout(row)
        self.input_box = QtWidgets.QGroupBox(self)
        input_field_layout = QtWidgets.QVBoxLayout()
        self.input_box.setLayout(input_field_layout)
        layout.addWidget(self.input_box)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def combined_names(self) -> str:
        """Reads all of the input fields in order and returns a string."""
        return ", ".join(self.result_tuple)

    @property
    def result_tuple(self) -> tuple:
        return tuple([f.text() for f in self.input_fields if f.text()])

    def changed(self) -> None:
        """
        Actions when the text within the TupleNameDialog is edited by the user
        """
        # rebuild the combined name example
        self.view_name.setText(f"'({self.combined_names})'")

        # disable the button (and its outline) when all fields are empty
        if self.combined_names == "":
            self.buttons.buttons()[0].setDefault(False)
            self.buttons.buttons()[0].setDisabled(True)
        # enable when that's not the case (anymore)
        else:
            self.buttons.buttons()[0].setDisabled(False)
            self.buttons.buttons()[0].setDefault(True)

    def add_input_field(self, text: str) -> None:
        edit = QtWidgets.QLineEdit(text, self)
        edit.textChanged.connect(self.changed)
        self.input_fields.append(edit)
        self.input_box.layout().addWidget(edit)

    @classmethod
    def get_combined_name(
        cls,
        parent: QtWidgets.QWidget,
        title: str,
        label: str,
        fields: tuple,
        extra: str = "Extra",
    ) -> "TupleNameDialog":
        """
        Set-up a TupleNameDialog pop-up with supplied title + label. Construct fields
        for each field of the supplied tuple. Last field of the tuple is appended with
        the extra string, to avoid duplicates.
        """
        obj = cls(parent)
        obj.setWindowTitle(title)
        obj.name_label.setText(label)

        # set up a field for each tuple element
        for i, field in enumerate(fields):
            field_content = str(field)

            # if it's the last element, add extra to the string
            if i + 1 == len(fields):
                field_content += extra
            obj.add_input_field(field_content)
        obj.input_box.updateGeometry()
        obj.changed()
        return obj
