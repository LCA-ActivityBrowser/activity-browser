from qtpy import QtCore, QtGui, QtWidgets


class ABListEditDialog(QtWidgets.QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit List/Tuple")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)

        # Table
        self.list = QtWidgets.QListWidget(self)
        self.list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(QtGui.Qt.MoveAction)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)

        layout.addWidget(self.list)

        # OK/Cancel
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.button_box)

        # Signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.load_data(data)

        self.list.itemChanged.connect(self.on_item_changed)

    def load_data(self, data):
        for value in data:
            self._append_item(str(value))
        self._append_add_field()

    def _append_item(self, text=""):
        item = QtWidgets.QListWidgetItem(text)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.list.addItem(item)

    def _append_add_field(self):
        """Always keep a final row with placeholder text."""
        item = QtWidgets.QListWidgetItem("add field")
        item.setFlags(QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        item.setForeground(QtCore.Qt.gray)
        self.list.addItem(item)

    def on_item_changed(self, item: QtWidgets.QListWidgetItem):
        row = self.list.row(item)
        last_row = self.list.count() - 1

        # User edited the placeholder row -> convert it to real row and add new placeholder
        if row == last_row and item.text().strip() and item.text() != "add field":
            self._append_add_field()
            item.setFlags(item.flags() | QtCore.Qt.ItemIsDragEnabled)
            item.setForeground(QtCore.Qt.black)
            return

        # If user clears a normal row, remove it
        elif row != last_row and not item.text().strip():
            self.list.takeItem(row)
            return

        # Restore placeholder if someone empties the last row
        elif row == last_row and not item.text().strip():
            item.setForeground(QtCore.Qt.gray)
            item.setText("add field")
            return

    def get_data(self, as_tuple=False):
        values = []
        last_row = self.list.count() - 1
        for row in range(self.list.count()):
            if row == last_row:
                continue  # skip the "add field" row
            item = self.list.item(row)
            if item and item.text().strip():
                values.append(item.text().strip())
        return tuple(values) if as_tuple else values


