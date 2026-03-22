from typing import List

from qtpy import QtWidgets


class ABDatabaseSelectionDialog(QtWidgets.QDialog):
    """Dialog to select one or more databases for export."""

    def __init__(self, parent=None, databases=None, title="Select databases"):
        super().__init__(parent=parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)

        self.db_list_widget = QtWidgets.QListWidget(self)
        self.db_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for db_name in databases:
            item = QtWidgets.QListWidgetItem(db_name)
            self.db_list_widget.addItem(item)
        layout.addWidget(self.db_list_widget)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_databases(self) -> List[str]:
        """Return the list of selected database names."""
        selected_items = self.db_list_widget.selectedItems()
        return [item.text() for item in selected_items]
