# -*- coding: utf-8 -*-
from PySide2 import QtGui, QtWidgets
from PySide2.QtCore import QRegExp, Slot

from ..style import style_group_box


class ForceInputDialog(QtWidgets.QDialog):
    """ Due to QInputDialog not allowing 'ok' button to be disabled when
    nothing is entered, we have this.

    https://stackoverflow.com/questions/48095573/how-to-disable-ok-button-in-qinputdialog-if-nothing-is-typed
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QtWidgets.QLabel()
        self.input = QtWidgets.QLineEdit()
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.input.textChanged.connect(self.changed)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def output(self):
        return self.input.text()

    @Slot(name="inputChanged")
    def changed(self):
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(bool(self.input.text()))

    @classmethod
    def get_text(cls, parent: QtWidgets.QWidget, title: str, label: str, text: str = "") -> 'ForceInputDialog':
        obj = cls(parent)
        obj.setWindowTitle(title)
        obj.label.setText(label)
        obj.input.setText(text)
        return obj


class TupleNameDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name_label = QtWidgets.QLabel("New name")
        self.view_name = QtWidgets.QLabel()
        self.no_comma_validator = QtGui.QRegExpValidator(QRegExp("[^,]+"))
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
        self.input_box.setStyleSheet(style_group_box.border_title)
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
        result = [f.text() for f in self.input_fields if f.text()]
        if not self.input_fields[-1].text():
            result.append(self.input_fields[-1].placeholderText())
        return tuple(result)

    @Slot(name="inputChanged")
    def changed(self) -> None:
        """Rebuild the view_name with text from all of the input fields."""
        self.view_name.setText("'({})'".format(self.combined_names))

    def add_input_field(self, text: str, placeholder: str = None) -> None:
        edit = QtWidgets.QLineEdit(text, self)
        edit.setPlaceholderText(placeholder or "")
        edit.setValidator(self.no_comma_validator)
        edit.textChanged.connect(self.changed)
        self.input_fields.append(edit)
        self.input_box.layout().addWidget(edit)

    @classmethod
    def get_combined_name(cls, parent: QtWidgets.QWidget, title: str, label: str,
                          fields: tuple, extra: str = "Extra") -> 'TupleNameDialog':
        obj = cls(parent)
        obj.setWindowTitle(title)
        obj.name_label.setText(label)
        for field in fields:
            obj.add_input_field(str(field))
        obj.add_input_field("", extra)
        obj.input_box.updateGeometry()
        obj.changed()
        return obj
