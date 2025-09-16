from qtpy import QtCore, QtGui, QtWidgets


class ABListEditDialog(QtWidgets.QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit List/Tuple")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)

        # Table
        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(1)
        self.table.horizontalHeader().setHidden(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.table.setDragDropOverwriteMode(False)
        self.table.setEditTriggers(QtWidgets.QTableWidget.AllEditTriggers)

        layout.addWidget(self.table)

        # OK/Cancel
        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.button_box)

        # Signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.load_data(data)

        self.table.itemChanged.connect(self.handle_item_changed)

    def load_data(self, data):
        self.table.setRowCount(0)
        for value in data:
            self._append_item(str(value))
        self._append_add_field()

    def _append_item(self, text=""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        item = QtWidgets.QTableWidgetItem(text)
        self.table.setItem(row, 0, item)

    def _append_add_field(self):
        """Always keep a final row with placeholder text."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        item = QtWidgets.QTableWidgetItem("")
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        item.setForeground(QtCore.Qt.gray)
        item.setText("add field")
        self.table.setItem(row, 0, item)

    def handle_item_changed(self, item: QtWidgets.QTableWidgetItem):
        row = item.row()
        last_row = self.table.rowCount() - 1

        # User edited the placeholder row -> convert it to real row and add new placeholder
        if row == last_row and item.text().strip() and item.text() != "add field":
            self._append_add_field()
            item.setForeground(QtCore.Qt.black)
            return

        # If user clears a normal row, remove it
        elif row != last_row and not item.text().strip():
            self.table.removeRow(row)
            return

        # Restore placeholder if someone empties the last row
        elif row == last_row and not item.text().strip():
            item.setForeground(QtCore.Qt.gray)
            item.setText("add field")
            return

    def get_data(self, as_tuple=False):
        values = []
        last_row = self.table.rowCount() - 1
        for row in range(self.table.rowCount()):
            if row == last_row:
                continue  # skip the "add field" row
            item = self.table.item(row, 0)
            if item and item.text().strip():
                values.append(item.text().strip())
        return tuple(values) if as_tuple else values
