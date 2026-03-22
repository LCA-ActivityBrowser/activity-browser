
from typing import Optional, Tuple
from qtpy.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QWidget


class NewNodeDialog(QDialog):
    """
    Gathers the paremeters for creating a new process.
    """

    def __init__(self, process: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QGridLayout()
        row = 0
        if process:
            self.setWindowTitle("New process")
            layout.addWidget(QLabel("Process name"), row, 0)
        else:
            self.setWindowTitle("New product")
            layout.addWidget(QLabel("Product name"), row, 0)
        self._process_name_edit = QLineEdit()
        self._process_name_edit.textChanged.connect(self._handle_text_changed)
        layout.addWidget(self._process_name_edit, row, 1)
        row += 1
        self._ref_product_name_edit = QLineEdit()
        if process:
            layout.addWidget(QLabel("Product name"), row, 0)
            layout.addWidget(self._ref_product_name_edit, row, 1)
            row += 1
        layout.addWidget(QLabel("Unit"), row, 0)
        self._unit_edit = QLineEdit("kilogram")
        layout.addWidget(self._unit_edit, row, 1)
        row += 1
        layout.addWidget(QLabel("Location"), row, 0)
        default_loc = "GLO" if process else ""
        self._location_edit = QLineEdit(default_loc)
        layout.addWidget(self._location_edit, row, 1)
        row += 1
        self._ok_button = QPushButton("OK")
        self._ok_button.clicked.connect(self.accept)
        self._ok_button.setEnabled(False)
        layout.addWidget(self._ok_button, row, 0)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button, row, 1)
        self.setLayout(layout)

    def _handle_text_changed(self, text: str):
        self._ok_button.setEnabled(text != "")
        self._ref_product_name_edit.setPlaceholderText(text)

    def get_new_process_data(self) -> Tuple[str, str, str, str]:
        """Return the parameters the user entered."""
        return (
                self._process_name_edit.text(),
                self._ref_product_name_edit.text(),
                self._unit_edit.text(),
                self._location_edit.text()
            )


