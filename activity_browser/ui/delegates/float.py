# -*- coding: utf-8 -*-
import math

from qtpy import QtCore, QtGui, QtWidgets


class FloatDelegate(QtWidgets.QStyledItemDelegate):
    """For managing and validating entered float values."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def displayText(self, value, locale):
        try:
            value = float(value)
        except ValueError:
            value = math.nan

        if math.isnan(value):
            return ""
        return str(value)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        locale = QtCore.QLocale(QtCore.QLocale.English)
        locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
        validator = QtGui.QDoubleValidator()
        validator.setLocale(locale)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        data = index.data(QtCore.Qt.DisplayRole)

        try:
            value = float(data)
        except ValueError:
            value = math.nan

        editor.setText(format(value, '.10f').rstrip('0').rstrip('.'))

    def setModelData(
        self,
        editor: QtWidgets.QLineEdit,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Take the editor, read the given value and set it in the model"""
        try:
            value = float(editor.text())
            model.setData(index, value, QtCore.Qt.EditRole)
        except ValueError:
            pass
