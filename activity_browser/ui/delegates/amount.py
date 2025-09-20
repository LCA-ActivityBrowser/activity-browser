from qtpy import QtCore, QtGui, QtWidgets

class AmountDelegate(QtWidgets.QStyledItemDelegate):
    def displayText(self, value, locale):
        import math
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
        validator = QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"^[+-]?((\d+(\.\d*)?)|(\.\d+))([eE][+-]?\d+)?$"),
            editor)
        validator.setLocale(locale)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        import math

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


class AbsoluteAmountDelegate(AmountDelegate):
    def displayText(self, value, locale):
        return str(abs(float(super().displayText(value, locale))))

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        import math

        data = index.data(QtCore.Qt.DisplayRole)

        try:
            value = abs(float(data))
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
            old = float(index.data(QtCore.Qt.DisplayRole))

            if old < 0:
                value = value * -1

            model.setData(index, value, QtCore.Qt.EditRole)
        except ValueError:
            pass
