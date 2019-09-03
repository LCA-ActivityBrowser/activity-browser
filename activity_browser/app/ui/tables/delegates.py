# -*- coding: utf-8 -*-
from itertools import zip_longest
from typing import List, Optional

import brightway2 as bw
from PyQt5 import QtCore, QtGui, QtWidgets
from stats_arrays import uncertainty_choices

from ..icons import qicons


class FloatDelegate(QtWidgets.QStyledItemDelegate):
    """ For managing and validating entered float values.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        locale = QtCore.QLocale(QtCore.QLocale.English)
        locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
        validator = QtGui.QDoubleValidator()
        validator.setLocale(locale)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        data = index.data(QtCore.Qt.DisplayRole)
        value = float(data) if data else 0
        editor.setText(str(value))

    def setModelData(self, editor: QtWidgets.QLineEdit, model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        try:
            value = float(editor.text())
            model.setData(index, value, QtCore.Qt.EditRole)
        except ValueError:
            pass


class StringDelegate(QtWidgets.QStyledItemDelegate):
    """ For managing and validating entered string values.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        value = index.data(QtCore.Qt.DisplayRole)
        # Avoid setting 'None' type value as a string
        value = str(value) if value else ""
        editor.setText(value)

    def setModelData(self, editor: QtWidgets.QLineEdit, model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        value = editor.text()
        model.setData(index, value, QtCore.Qt.EditRole)


class DatabaseDelegate(QtWidgets.QStyledItemDelegate):
    """ Nearly the same as the string delegate, but presents as
    a combobox menu containing the databases of the current project.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.insertItems(0, bw.databases.list)
        return editor

    def setEditorData(self, editor: QtWidgets.QComboBox, index: QtCore.QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        value = str(index.data(QtCore.Qt.DisplayRole))
        editor.setCurrentText(value)

    def setModelData(self, editor: QtWidgets.QComboBox, model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        """ Take the editor, read the given value and set it in the model.
        """
        value = editor.currentText()
        model.setData(index, value, QtCore.Qt.EditRole)


class CheckboxDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None

    def paint(self, painter, option, index):
        """ Paint the cell with a styled option button, showing a checkbox

        See links below for inspiration:
        https://stackoverflow.com/a/11778012
        https://stackoverflow.com/q/15235273
        """
        value = bool(index.data(QtCore.Qt.DisplayRole))
        button = QtWidgets.QStyleOptionButton()
        button.state = QtWidgets.QStyle.State_Enabled
        button.state |= QtWidgets.QStyle.State_Off if not value else QtWidgets.QStyle.State_On
        button.rect = option.rect
        # button.text = "False" if not value else "True"  # This also adds text
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_CheckBox, button, painter)


class ViewOnlyDelegate(QtWidgets.QStyledItemDelegate):
    """ Disable the editor functionality to allow specific columns of an
    editable table to be view-only.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None


class OrderedListInputDialog(QtWidgets.QDialog):
    """ Mostly cobbled together from: https://stackoverflow.com/a/41310284
    and https://stackoverflow.com/q/26936585
    """
    def __init__(self, parent=None, flags=QtCore.Qt.Window):
        super().__init__(parent=parent, flags=flags)
        self.setWindowTitle("Select and order items")

        form = QtWidgets.QFormLayout(self)
        self.list_view = QtWidgets.QListView(self)
        self.list_view.setDragDropMode(QtWidgets.QListView.InternalMove)
        form.addRow(self.list_view)
        model = QtGui.QStandardItemModel(self.list_view)
        self.list_view.setModel(model)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.show()

    @staticmethod
    def add_items_value(items: list, value: bool=False) -> List[tuple]:
        """ Helper method, takes a list of items and adds given bool value,
        returning a list of tuples.
        """
        return [
            (i, b) for i, b in zip_longest(items, [], fillvalue=value)
        ]

    def set_items(self, items: List[tuple]):
        model = self.list_view.model()
        model.clear()
        for i, checked in items:
            item = QtGui.QStandardItem(i)
            item.setCheckable(True)
            item.setCheckState(checked)
            model.appendRow(item)
        self.list_view.setModel(model)

    def items_selected(self) -> list:
        model = self.list_view.model()
        selected = []
        for item in [model.item(i) for i in range(model.rowCount())]:
            if item.checkState():
                selected.append(item.text())
        return selected


class ListDelegate(QtWidgets.QStyledItemDelegate):
    """ For managing and validating entered string values
    https://stackoverflow.com/a/40275439
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QWidget(parent)
        dialog = OrderedListInputDialog(editor, QtCore.Qt.Window)

        # Check which table is asking for a list
        if hasattr(parent, "table_name") and parent.table_name == "activity_parameter":
            items = parent.get_activity_groups()
            unchecked_items = dialog.add_items_value(items)
            dialog.set_items(unchecked_items)

        return editor

    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        dialog = editor.findChild(OrderedListInputDialog)
        value = index.data(QtCore.Qt.DisplayRole)
        if value:
            value_list = [i.lstrip() for i in value.split(",")]
        else:
            value_list = []

        parent = self.parent()
        if hasattr(parent, "table_name") and parent.table_name == "activity_parameter":
            groups = parent.get_activity_groups(value_list)
            unchecked = dialog.add_items_value(groups)
            checked = dialog.add_items_value(value_list, True)
            dialog.set_items(checked + unchecked)

    def setModelData(self, editor: QtWidgets.QWidget, model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        dialog = editor.findChild(OrderedListInputDialog)
        value = ", ".join(map(lambda i: str(i), dialog.items_selected()))
        model.setData(index, value, QtCore.Qt.EditRole)


class UncertaintyDelegate(QtWidgets.QStyledItemDelegate):
    """ A combobox containing the sorted list of possible uncertainties
    `setModelData` stores the integer id of the selected uncertainty
    distribution.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.choices = {
            u.description: u.id for u in uncertainty_choices.choices
        }

    def createEditor(self, parent, option, index):
        """ Create a list of descriptions of the uncertainties we have.
        Note that the `choices` attribute of uncertainty_choices is already
        sorted by id.
        """
        editor = QtWidgets.QComboBox(parent)
        items = sorted(self.choices, key=self.choices.get)
        editor.insertItems(0, items)
        return editor

    def setEditorData(self, editor: QtWidgets.QComboBox, index: QtCore.QModelIndex):
        """ Lookup the description text set in the model using the reverse
        dictionary for the uncertainty choices.

        Note that the model presents the integer value as a string (the
        description of the uncertainty distribution), so we cannot simply
        take the value and set the index in that way.
        """
        value = index.data(QtCore.Qt.DisplayRole)
        editor.setCurrentIndex(self.choices.get(value, 0))

    def setModelData(self, editor: QtWidgets.QComboBox, model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        """ Read the current index of the combobox and return that to the model.
        """
        value = editor.currentIndex()
        model.setData(index, value, QtCore.Qt.EditRole)


class FormulaDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, flags=QtCore.Qt.Window):
        super().__init__(parent=parent, flags=flags)
        self.setWindowTitle("Build a formula")

        # 6 broad by 6 deep.
        grid = QtWidgets.QGridLayout(self)
        self.text_field = QtWidgets.QPlainTextEdit(self)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.ButtonBox
        ))
        self.parameters = QtWidgets.QTableView(self)
        model = QtGui.QStandardItemModel(self)
        self.parameters.setModel(model)
        self.new_parameter = QtWidgets.QPushButton(
            qicons.add, "New parameter", self
        )
        self.new_parameter.setEnabled(False)

        grid.addWidget(self.text_field, 0, 0, 5, 3)
        grid.addWidget(buttons, 5, 0, 1, 3)
        grid.addWidget(self.parameters, 0, 3, 5, 3)
        grid.addWidget(self.new_parameter, 5, 3, 1, 3)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.show()

    def insert_parameters(self, items: list) -> None:
        """ Take the given list of parameter names, amounts and types, insert
        them into the model.
        """
        model = self.parameters.model()
        model.clear()
        model.setHorizontalHeaderLabels(["Name", "Amount", "Type"])
        for x, item in enumerate(items):
            for y, value in enumerate(item):
                model_item = QtGui.QStandardItem(str(value))
                model_item.setEditable(False)
                model.setItem(x, y, model_item)
        self.parameters.resizeColumnsToContents()

    def set_formula(self, value) -> None:
        """ Take the formula and set it to the text_field widget.
        """
        value = "" if value is None else str(value)
        self.text_field.setPlainText(value)

    def get_formula(self) -> Optional[str]:
        """ Look into the text_field, validate formula and return it.
        """
        value = self.text_field.toPlainText()
        # TODO: formula validation here?
        return value if value != "" else None


class FormulaDelegate(QtWidgets.QStyledItemDelegate):
    """ An extensive delegate to allow users to build and validate formulas
    The delegate spawns a dialog containing:
      - An editable textfield for the formula.
      - A listview containing parameter names that can be used in the formula
      - Ok and Cancel buttons, on Ok, validate the formula before saving
    For hardmode: also allow the user to create a new parameter from WITHIN
    the delegate dialog itself. Requiring us to also include refreshing
    for the parameter list.
    """
    ACCEPTED_TABLES = {"project_parameter", "database_parameter",
                       "activity_parameter", "product", "technosphere",
                       "biosphere"}

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QWidget(parent)
        dialog = FormulaDialog(editor, QtCore.Qt.Window)
        dialog.setModal(True)
        return editor

    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        dialog = editor.findChild(FormulaDialog)
        data = index.data(QtCore.Qt.DisplayRole)

        parent = self.parent()
        # Check which table is asking for a list
        if getattr(parent, "table_name", "") in self.ACCEPTED_TABLES:
            items = parent.get_usable_parameters()
            dialog.insert_parameters(items)
            dialog.set_formula(data)

    def setModelData(self, editor: QtWidgets.QWidget, model: QtCore.QAbstractItemModel,
                     index: QtCore.QModelIndex):
        """ Take the editor, read the given value and set it in the model.

        If the new formula is the same as the existing one, do not call setData
        """
        dialog = editor.findChild(FormulaDialog)
        value = dialog.get_formula()
        if model.data(index, QtCore.Qt.DisplayRole) == value:
            return
        model.setData(index, value, QtCore.Qt.EditRole)
