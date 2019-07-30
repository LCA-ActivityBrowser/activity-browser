# -*- coding: utf-8 -*-
from itertools import zip_longest
from typing import List

import brightway2 as bw
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt5.QtGui import QDoubleValidator, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QListView,
    QStyledItemDelegate, QWidget)
from stats_arrays import uncertainty_choices

from . import parameters


class FloatDelegate(QStyledItemDelegate):
    """ For managing and validating entered float values
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setValidator(QDoubleValidator())
        return editor

    def setEditorData(self, editor: QLineEdit, index: QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        data = index.data(Qt.DisplayRole)
        value = float(data) if data else 0
        editor.setText(str(value))

    def setModelData(self, editor: QLineEdit, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        value = float(editor.text())
        model.setData(index, value, Qt.EditRole)


class StringDelegate(QStyledItemDelegate):
    """ For managing and validating entered string values
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

    def setEditorData(self, editor: QLineEdit, index: QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        value = index.data(Qt.DisplayRole)
        # Avoid setting 'None' type value as a string
        value = str(value) if value else ""
        editor.setText(value)

    def setModelData(self, editor: QLineEdit, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        value = editor.text()
        model.setData(index, value, Qt.EditRole)


class DatabaseDelegate(QStyledItemDelegate):
    """ Nearly the same as the string delegate, but presents as
    a combobox menu containing the databases of the current project
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.insertItems(0, bw.databases.list)
        return editor

    def setEditorData(self, editor: QComboBox, index: QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        value = str(index.data(Qt.DisplayRole))
        editor.setCurrentText(value)

    def setModelData(self, editor: QComboBox, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        value = editor.currentText()
        model.setData(index, value, Qt.EditRole)


class ViewOnlyDelegate(QStyledItemDelegate):
    """ Disable the editor functionality to allow specific columns
     to be view-only
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None


class OrderedListInputDialog(QDialog):
    """ Mostly cobbled together from: https://stackoverflow.com/a/41310284
    and https://stackoverflow.com/q/26936585
    """
    def __init__(self, parent=None, flags=Qt.Window):
        super().__init__(parent=parent, flags=flags)
        self.setWindowTitle("Select and order items")

        form = QFormLayout(self)
        self.list_view = QListView(self)
        self.list_view.setDragDropMode(QListView.InternalMove)
        form.addRow(self.list_view)
        model = QStandardItemModel(self.list_view)
        self.list_view.setModel(model)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
            item = QStandardItem(i)
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


class ListDelegate(QStyledItemDelegate):
    """ For managing and validating entered string values

    https://stackoverflow.com/a/40275439
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QWidget(parent)
        dialog = OrderedListInputDialog(editor, Qt.Window)

        # Check which table is asking for a list
        if isinstance(parent, parameters.ActivityParameterTable):
            items = parameters.ActivityParameterTable.get_activity_groups()
            unchecked_items = dialog.add_items_value(items)
            dialog.set_items(unchecked_items)

        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        """ Populate the editor with data if editing an existing field.
        """
        dialog = editor.findChild(OrderedListInputDialog)
        value = index.data(Qt.DisplayRole)
        if value:
            value_list = [i.lstrip() for i in value.split(",")]
        else:
            value_list = []

        if isinstance(self.parent(), parameters.ActivityParameterTable):
            groups = parameters.ActivityParameterTable.get_activity_groups(value_list)
            unchecked = dialog.add_items_value(groups)
            checked = dialog.add_items_value(value_list, True)
            dialog.set_items(checked + unchecked)

    def setModelData(self, editor: QWidget, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        dialog = editor.findChild(OrderedListInputDialog)
        value = ", ".join(map(lambda i: str(i), dialog.items_selected()))
        model.setData(index, value, Qt.EditRole)


class UncertaintyDelegate(QStyledItemDelegate):
    """ A combobox containing the sorted list of possible uncertainties

    `setModelData` stores the integer id of the selected uncertainty
    distribution
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rev_uncertainty = {
            u.description: u.id for u in uncertainty_choices.choices
        }  # ;)

    def createEditor(self, parent, option, index):
        """ Create a list of descriptions of the uncertainties we have.

        Note that the `choices` attribute of uncertainty_choices is already
        sorted by id.
        """
        editor = QComboBox(parent)
        items = [c.description for c in uncertainty_choices.choices]
        editor.insertItems(0, items)
        return editor

    def setEditorData(self, editor: QComboBox, index: QModelIndex):
        """ Lookup the description text set in the model using the reverse
        dictionary for the uncertainty choices.

        Note that the model presents the integer value as a string (the
        description of the uncertainty distribution), so we cannot simply
        take the value and set the index in that way.
        """
        value = index.data(Qt.DisplayRole)
        editor.setCurrentIndex(self.rev_uncertainty.get(value, 0))

    def setModelData(self, editor: QComboBox, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Read the current index of the combobox and return that to the model
        """
        value = editor.currentIndex()
        model.setData(index, value, Qt.EditRole)
