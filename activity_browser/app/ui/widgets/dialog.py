# -*- coding: utf-8 -*-
from PySide2 import QtWidgets
from PySide2.QtCore import Slot


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
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    @classmethod
    def get_text(cls, parent: QtWidgets.QWidget, title: str, label: str, text: str = "") -> 'ForceInputDialog':
        obj = cls(parent)
        obj.setWindowTitle(title)
        obj.label.setText(label)
        obj.input.setText(text)
        return obj
