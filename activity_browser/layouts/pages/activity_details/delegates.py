from qtpy import QtWidgets, QtCore, QtGui

from activity_browser import actions


class PropertyDelegate(QtWidgets.QStyledItemDelegate):

    def displayText(self, value, locale):
        if not isinstance(value, dict):
            return "Undefined"

        if sorted(value.keys()) != ["amount", "normalize", "unit"]:
            return "Faulty property"

        display = f"{value["amount"]} {value["unit"]}"
        return display

    def createEditor(self, parent, option, index):
        data = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if not data:
            return None

        editor = QtWidgets.QLineEdit(parent)
        validator = QtGui.QDoubleValidator()
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        data = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        editor.setText(str(data["amount"]))

    def setModelData(self, editor: QtWidgets.QLineEdit, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        """Take the editor, read the given value and set it in the model"""
        try:
            value = float(editor.text())
            model.setData(index, value, QtCore.Qt.EditRole)
        except ValueError:
            pass
