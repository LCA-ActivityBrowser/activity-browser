# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List, Tuple

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


class DatabaseRelinkDialog(QtWidgets.QDialog):
    LABEL_TEXT = (
        "A database could not be found in project, attempt to relink the"
        " exchanges to a different database?"
        "\n\nReplace database '{}' with:"
    )
    RELINK_EXISTING = (
        "Relink exchanges from database '{}' to:"
        "\n\nTarget database:"
    )
    LINK_UNKNOWN = (
        "Link exchanges from database '{}' to:"
        "\n\nTarget database:"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database relinking")
        self.label = QtWidgets.QLabel("")
        self.choice = QtWidgets.QComboBox()
        self.choice.addItems(["-----"])
        self.choice.setDisabled(True)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.choice)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def new_db(self) -> str:
        return self.choice.currentText()

    @classmethod
    def start_relink(cls, parent: QtWidgets.QWidget, db: str, options: List[str]) -> 'DatabaseRelinkDialog':
        obj = cls(parent)
        obj.label.setText(cls.LABEL_TEXT.format(db))
        obj.choice.clear()
        obj.choice.addItems(options)
        obj.choice.setEnabled(True)
        return obj

    @classmethod
    def relink_existing(cls, parent: QtWidgets.QWidget, db: str, options: List[str]) -> 'DatabaseRelinkDialog':
        obj = cls(parent)
        obj.label.setText(cls.RELINK_EXISTING.format(db))
        obj.choice.clear()
        obj.choice.addItems(options)
        obj.choice.setEnabled(True)
        return obj

    @classmethod
    def link_new(cls, parent, db: str, options: List[str]) -> 'DatabaseRelinkDialog':
        obj = cls(parent)
        obj.setWindowTitle("Database Linking")
        obj.label.setText(cls.LINK_UNKNOWN.format(db))
        obj.choice.clear()
        obj.choice.addItems(options)
        if db in options:
            obj.choice.setCurrentText(db)
        obj.choice.setEnabled(True)
        return obj


class DatabaseLinkingDialog(QtWidgets.QDialog):
    """Display all of the possible links in a single dialog for the user.

    Allow users to select alternate database links."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database linking")

        self.db_label = QtWidgets.QLabel()
        self.label_choices = []
        self.grid_box = QtWidgets.QGroupBox("Database links:")
        self.grid = QtWidgets.QGridLayout()
        self.grid_box.setLayout(self.grid)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.db_label)
        layout.addWidget(self.grid_box)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def relink(self) -> dict:
        """Returns a dictionary of str -> str key/values, showing which keys
        should be linked to which values.

        Only returns key/value pairs if they differ.
        """
        return {
            label.text(): combo.currentText() for label, combo in self.label_choices
            if label.text() != combo.currentText()
        }

    @property
    def links(self) -> dict:
        """Returns a dictionary of str -> str key/values, showing which keys
        should be linked to which values.
        """
        return {
            label.text(): combo.currentText() for label, combo in self.label_choices
        }

    @classmethod
    def construct_dialog(cls, label: str, options: List[Tuple[str, List[str]]],
                         parent: QtWidgets.QWidget = None) -> 'DatabaseLinkingDialog':
        obj = cls(parent)
        obj.db_label.setText(label)
        # Start at 1 because row 0 is taken up by the db_label
        for i, item in enumerate(options):
            label = QtWidgets.QLabel(item[0])
            combo = QtWidgets.QComboBox()
            combo.addItems(item[1])
            combo.setCurrentText(item[0])
            obj.label_choices.append((label, combo))
            obj.grid.addWidget(label, i, 0, 1, 2)
            obj.grid.addWidget(combo, i, 2, 1, 2)
        obj.updateGeometry()
        return obj

    @classmethod
    def relink_sqlite(cls, db: str, options: List[Tuple[str, List[str]]],
                      parent=None) -> 'DatabaseLinkingDialog':
        label = "Relinking exchanges from database '{}'.".format(db)
        return cls.construct_dialog(label, options, parent)

    @classmethod
    def relink_bw2package(cls, options: List[Tuple[str, List[str]]],
                          parent=None) -> 'DatabaseLinkingDialog':
        label = ("Some database(s) could not be found in the current project,"
                 " attempt to relink the exchanges to a different database?")
        return cls.construct_dialog(label, options, parent)

    @classmethod
    def relink_excel(cls, options: List[Tuple[str, List[str]]],
                     parent=None) -> 'DatabaseLinkingDialog':
        label = "Customize database links for exchanges in the imported database."
        return cls.construct_dialog(label, options, parent)
