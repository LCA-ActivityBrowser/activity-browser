from qtpy import QtWidgets, QtCore


class PropertyDelegate(QtWidgets.QStyledItemDelegate):
    """
    A delegate for displaying and editing property values in the tree view.
    """

    def displayText(self, value, locale):
        """
        Returns the display text for the given value.

        Args:
            value: The value to display.
            locale: The locale to use for formatting.

        Returns:
            str: The display text.
        """
        if not isinstance(value, dict):
            return "Undefined"

        if sorted(value.keys()) != ["amount", "normalize", "unit"]:
            return "Faulty property"

        display = f"{value['amount']} {value['unit']}"
        return display

    def createEditor(self, parent, option, index):
        """
        Creates an editor for the given index.

        Args:
            parent: The parent widget.
            option: The style options.
            index: The index to edit.

        Returns:
            QtWidgets.QLineEdit: The editor widget.
        """
        data = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if not data:
            return None

        editor = QtWidgets.QLineEdit(parent)
        # validator = QtGui.QDoubleValidator()
        # editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """
        Populates the editor with data if editing an existing field.

        Args:
            editor (QtWidgets.QLineEdit): The editor widget.
            index (QtCore.QModelIndex): The index to edit.
        """
        data = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        editor.setText(str(data["amount"]))

    def setModelData(self, editor: QtWidgets.QLineEdit, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        """
        Takes the editor, reads the given value, and sets it in the model.

        Args:
            editor (QtWidgets.QLineEdit): The editor widget.
            model (QtCore.QAbstractItemModel): The model to update.
            index (QtCore.QModelIndex): The index to update.
        """
        try:
            value = float(editor.text())
            model.setData(index, value, QtCore.Qt.EditRole)
        except ValueError:
            pass