
from typing import Optional, Tuple
from PySide2.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QWidget


class NewProcessDialog(QDialog):
    """
    Gathers the paremeters for creating a new process.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("New process")
        layout = QGridLayout()
        layout.addWidget(QLabel("Process name"), 0, 0)
        self._process_name_edit = QLineEdit()
        self._process_name_edit.textChanged.connect(self._handle_text_changed)
        layout.addWidget(self._process_name_edit, 0, 1)
        layout.addWidget(QLabel("Reference product name"), 1, 0)
        self._ref_product_name_edit = QLineEdit()
        layout.addWidget(self._ref_product_name_edit, 1, 1)
        layout.addWidget(QLabel("Unit"), 2, 0)
        self._unit_edit = QLineEdit("kilogram")
        layout.addWidget(self._unit_edit, 2, 1)
        layout.addWidget(QLabel("Location"), 3, 0)
        self._location_edit = QLineEdit("GLO")
        layout.addWidget(self._location_edit, 3, 1)
        self._ok_button = QPushButton("OK")
        self._ok_button.clicked.connect(self.accept)
        self._ok_button.setEnabled(False)
        layout.addWidget(self._ok_button, 4, 0)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button, 4, 1)
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


