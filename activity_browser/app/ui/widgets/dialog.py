# -*- coding: utf-8 -*-
from pathlib import Path

from PySide2 import QtGui, QtWidgets
from PySide2.QtCore import QRegExp, Slot

from ...bwutils.superstructure import get_sheet_names
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


class ChoiceSelectionDialog(QtWidgets.QDialog):
    """Given a number of options, select one of them."""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.input_box = QtWidgets.QGroupBox(self)
        self.input_box.setStyleSheet(style_group_box.border_title)
        input_field_layout = QtWidgets.QVBoxLayout()
        self.input_box.setLayout(input_field_layout)
        self.group = QtWidgets.QButtonGroup(self)
        self.group.setExclusive(True)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.input_box)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def choice(self) -> str:
        """Returns the name of the chosen option, allowing for a comparison"""
        checked = self.group.checkedButton()
        return checked.text()

    @classmethod
    def get_choice(cls, parent: QtWidgets.QWidget, *choices) -> 'ChoiceSelectionDialog':
        assert len(choices) > 0, "Must give choices to choose from."

        obj = cls(parent)
        obj.setWindowTitle("Select the option")

        iterable = iter(choices)
        first = QtWidgets.QRadioButton(str(next(iterable)))
        first.setChecked(True)
        obj.group.addButton(first)
        obj.input_box.layout().addWidget(first)
        for choice in iterable:
            btn = QtWidgets.QRadioButton(str(choice))
            obj.group.addButton(btn)
            obj.input_box.layout().addWidget(btn)
        obj.input_box.updateGeometry()
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


class ExcelReadDialog(QtWidgets.QDialog):
    SUFFIXES = {".xls", ".xlsx"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select excel file to read")

        self.path = None
        self.path_line = QtWidgets.QLineEdit()
        self.path_line.setReadOnly(True)
        self.path_line.textChanged.connect(self.changed)
        self.path_btn = QtWidgets.QPushButton("Browse")
        self.path_btn.clicked.connect(self.browse)
        self.import_sheet = QtWidgets.QComboBox()
        self.import_sheet.addItems(["-----"])
        self.import_sheet.setEnabled(False)
        self.complete = False

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.complete)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Path to file*"), 0, 0, 1, 1)
        grid.addWidget(self.path_line, 0, 1, 1, 2)
        grid.addWidget(self.path_btn, 0, 3, 1, 1)
        grid.addWidget(QtWidgets.QLabel("Excel sheet name"), 1, 0, 1, 1)
        grid.addWidget(self.import_sheet, 1, 1, 2, 1)

        input_box = QtWidgets.QGroupBox(self)
        input_box.setStyleSheet(style_group_box.border_title)
        input_box.setLayout(grid)
        layout.addWidget(input_box)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @Slot(name="browseFile")
    def browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption="Select scenario template file",
            filter="Excel (*.xlsx);; All Files (*.*)"
        )
        if path:
            self.path_line.setText(path)

    def update_combobox(self, file_path) -> None:
        self.import_sheet.blockSignals(True)
        self.import_sheet.clear()
        names = get_sheet_names(file_path)
        self.import_sheet.addItems(names)
        self.import_sheet.setEnabled(self.import_sheet.count() > 0)
        self.import_sheet.blockSignals(False)

    @Slot(name="pathChanged")
    def changed(self) -> None:
        """Determine if selected path is valid."""
        self.path = Path(self.path_line.text())
        self.complete = all([
            self.path.exists(), self.path.is_file(),
            self.path.suffix in self.SUFFIXES
        ])
        if self.complete:
            self.update_combobox(self.path)
        self.buttons.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(self.complete)
