# -*- coding: utf-8 -*-
from bw2data import databases
from qtpy import QtCore, QtWidgets


class DatabaseDelegate(QtWidgets.QStyledItemDelegate):
    """Nearly the same as the string delegate, but presents as
    a combobox menu containing the databases of the current project.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.insertItems(0, databases.list)
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
