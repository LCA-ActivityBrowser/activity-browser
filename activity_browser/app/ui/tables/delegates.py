# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt5.QtGui import QDoubleValidator, QRegExpValidator
from PyQt5.QtWidgets import (QComboBox, QItemDelegate, QLineEdit, QTextEdit,
                             QWidget)


class FloatDelegate(QItemDelegate):
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
        value = str(index.data(Qt.DisplayRole))
        editor.setText(value)

    def setModelData(self, editor: QLineEdit, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        value = float(editor.text())
        model.setData(index, value, Qt.EditRole)


class StringDelegate(QItemDelegate):
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
        value = str(index.data(Qt.DisplayRole))
        editor.setText(value)

    def setModelData(self, editor: QLineEdit, model: QAbstractItemModel,
                     index: QModelIndex):
        """ Take the editor, read the given value and set it in the model
        """
        value = editor.text()
        model.setData(index, value, Qt.EditRole)


class DatabaseDelegate(QItemDelegate):
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
