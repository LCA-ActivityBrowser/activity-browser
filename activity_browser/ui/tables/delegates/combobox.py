# -*- coding: utf-8 -*-
from typing import Callable, Union
from PySide2 import QtCore, QtWidgets


class ComboboxDelegate(QtWidgets.QStyledItemDelegate):
    """Generic Combobox delegate."""

    def __init__(self, data_source: Union[list[str], Callable[[], list[str]]], parent=None):
        super().__init__(parent)
        self._data_source = data_source

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        if callable(self._data_source):
            data = self._data_source()
        else:
            data = self._data_source
        editor.insertItems(0, data)
        return editor

    def setEditorData(self, editor: QtWidgets.QComboBox, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        value = str(index.data(QtCore.Qt.DisplayRole))
        editor.setCurrentText(value)

    def setModelData(
        self,
        editor: QtWidgets.QComboBox,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Take the editor, read the given value and set it in the model."""
        value = editor.currentText()
        model.setData(index, value, QtCore.Qt.EditRole)
