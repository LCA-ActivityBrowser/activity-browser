# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets


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
