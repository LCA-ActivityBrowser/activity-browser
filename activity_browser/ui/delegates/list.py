# -*- coding: utf-8 -*-
from itertools import zip_longest
from typing import List

from qtpy import QtCore, QtGui, QtWidgets


class OrderedListInputDialog(QtWidgets.QDialog):
    """Mostly cobbled together from: https://stackoverflow.com/a/41310284
    and https://stackoverflow.com/q/26936585
    """

    def __init__(self, parent=None, flags=QtCore.Qt.Window):
        super().__init__(parent=parent, f=flags)
        self.setWindowTitle("Select and order items")

        form = QtWidgets.QFormLayout(self)
        self.list_view = QtWidgets.QListView(self)
        self.list_view.setDragDropMode(QtWidgets.QListView.InternalMove)
        form.addRow(self.list_view)
        model = QtGui.QStandardItemModel(self.list_view)
        self.list_view.setModel(model)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        form.addRow(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.show()

    @staticmethod
    def add_items_value(items, value: bool = False) -> List[tuple]:
        """Helper method, takes a list of items and adds given bool value,
        returning a list of tuples.
        """
        return [(i, b) for i, b in zip_longest(items, [], fillvalue=value)]

    def set_items(self, items: List[tuple]):
        model = self.list_view.model()
        model.clear()
        for i, checked in items:
            item = QtGui.QStandardItem(i)
            item.setCheckable(True)
            if checked:
                item.setCheckState(QtCore.Qt.CheckState.Checked)
            else:
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
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
    """For managing and validating entered string values
    https://stackoverflow.com/a/40275439
    """
    def displayText(self, value, locale):
        if not isinstance(value, (list, tuple)):
            return str(value)
        return " > ".join(value)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QWidget(parent)
        dialog = OrderedListInputDialog(editor, QtCore.Qt.Window)
        dialog.accepted.connect(lambda: self.commitData.emit(editor))
        return editor

    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        dialog = editor.findChild(OrderedListInputDialog)
        value = index.data(QtCore.Qt.DisplayRole)
        values = [] if not value else [i.lstrip() for i in value.split(",")]

        parent = self.parent()
        if getattr(parent, "table_name") == "activity_parameter":
            groups = parent.get_activity_groups(index, values)
            unchecked = dialog.add_items_value(groups)
            checked = dialog.add_items_value(values, True)
            dialog.set_items(checked + unchecked)

    def setModelData(
        self,
        editor: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Take the editor, read the given value and set it in the model"""
        dialog = editor.findChild(OrderedListInputDialog)
        value = dialog.items_selected()
        model.setData(index, value, QtCore.Qt.EditRole)
