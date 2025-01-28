from qtpy import QtWidgets, QtCore, QtGui

from activity_browser import actions


class PropertyDelegate(QtWidgets.QStyledItemDelegate):

    def displayText(self, value, locale):
        if not value:
            return ""
        value = [str(x) for x in value]
        return " ".join(value)

    def createEditor(self, parent, option, index):
        data = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if not data:
            return None

        if data == ("Undefined",):
            item = index.internalPointer()
            prop_name = index.model().columns()[index.column()][10:]

            actions.FunctionPropertyAdd.run(item.exchange.input, prop_name)
            return None

        editor = QtWidgets.QLineEdit(parent)
        validator = QtGui.QDoubleValidator()
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        import math
        data = index.data(QtCore.Qt.ItemDataRole.DisplayRole)

        try:
            value = float(data[0])
        except ValueError:
            value = math.nan

        editor.setText(str(value))

    def setModelData(self, editor: QtWidgets.QLineEdit, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        """Take the editor, read the given value and set it in the model"""
        try:
            value = float(editor.text())
            model.setData(index, value, QtCore.Qt.EditRole)
        except ValueError:
            pass
