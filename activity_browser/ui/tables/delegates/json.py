from typing import Optional

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt, QDate
from qtpy.QtGui import QIntValidator, QDoubleValidator
from qtpy.QtWidgets import QLineEdit, QDateEdit


class JSONDelegate(QtWidgets.QStyledItemDelegate):
    """
    JSON Editor that supports multiple types (int, float, string, date (string))
    Assumes that the
    """

    def __init__(self, type_column: Optional[int] = None, parent=None):
        """
        :param type_column: column index of the type column
        """
        super().__init__(parent)
        self.type_column = type_column

    def createEditor(self, parent, option, index):
        type_index = index.model().index(index.row(), self.type_column)
        value_type = index.model().data(type_index, Qt.DisplayRole)
        if value_type == "int":
            editor = QLineEdit(parent)
            editor.setValidator(QIntValidator())
        elif value_type == "float":
            editor = QLineEdit(parent)
            editor.setValidator(QDoubleValidator())
        elif value_type == "string":
            editor = QLineEdit(parent)
        elif value_type == "date":
            editor = QDateEdit(parent)
        else:
            editor = super().createEditor(parent, option, index)
        editor.setProperty("value_type", value_type)
        return editor

    def setEditorData(self, editor, index):
        current_text = index.model().data(index, Qt.DisplayRole)
        value_type = editor.property("value_type")
        if value_type in ["int", "float", "string"]:
            editor.setText(current_text)
        elif value_type == "date":
            editor.setDate(QDate.fromString(current_text, "yyyy-MM-dd"))
            editor.setCalendarPopup(True)
        else:
            editor.setText(current_text)

    def setModelData(
        self,
        editor: QtWidgets.QLineEdit,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Take the editor, read the given value and set it in the model"""
        value_type = editor.property("value_type")
        if value_type == "int":
            try:
                value = int(editor.text())
                model.setData(index, value, QtCore.Qt.EditRole)
            except ValueError:
                pass
        elif value_type == "float":
            try:
                value = float(editor.text())
                model.setData(index, value, QtCore.Qt.EditRole)
            except ValueError:
                pass
        elif value_type == "string":
            value = editor.text()
            model.setData(index, value, QtCore.Qt.EditRole)
        elif value_type == "date":
            editor: QDateEdit
            value = editor.date().toPython().isoformat()
            model.setData(index, value, QtCore.Qt.EditRole)
        else:
            value = editor.text()
            model.setData(index, value, QtCore.Qt.EditRole)
