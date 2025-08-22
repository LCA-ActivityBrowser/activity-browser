from qtpy import QtWidgets, QtCore

from activity_browser import application, settings, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

from .database_open import DatabaseOpen


class DatabaseNew(ABAction):
    """
    Executes the process of creating a new database.

    This method retrieves the database name and backend type from the `NewDatabaseDialog`.
    It validates the input to ensure the name is not empty and does not already exist.
    If the input is valid, it creates and registers a new database, then opens it.

    Steps:
    - Open the `NewDatabaseDialog` to get the database name and backend type.
    - Return if the dialog is canceled or the name is empty.
    - Check if the database name already exists and show an error message if it does.
    - Create a new database with the specified name and backend type.
    - Register the database with default settings (not searchable, not read-only).
    - Open the newly created database.

    Raises:
        None
    """
    icon = qicons.add
    text = "New database..."
    tool_tip = "Make a new database"

    @staticmethod
    @exception_dialogs
    def run():
        name, backend, ok = NewDatabaseDialog.get_new_database_data()

        if not ok or not name:
            return

        if name in bd.databases:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible",
                "A database with this name already exists.",
            )
            return

        db = bd.Database(name, backend if backend else "functional_sqlite")
        db.register(searchable=False, read_only=False)

        DatabaseOpen.run([name])


class NewDatabaseDialog(QtWidgets.QDialog):
    """
    A dialog for creating a new database.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Database")
        self.setModal(True)

        self.name_input = QtWidgets.QLineEdit(self)
        self.name_input.setPlaceholderText("Enter database name")
        self.name_input.textChanged.connect(self.validate)

        self.backend_dropdown = QtWidgets.QComboBox(self)
        self.backend_dropdown.addItems(["functional_sqlite", "sqlite"])

        self.create_button = QtWidgets.QPushButton("Create", self)
        self.create_button.setDisabled(True)
        self.create_button.clicked.connect(self.accept)

        self.build_layout()

    @classmethod
    def get_new_database_data(cls) -> tuple[str, str, bool]:
        """
        Opens a dialog to collect data for creating a new database.

        Returns:
            tuple[str, str, bool]: A tuple containing:
                - The name of the new database (str).
                - The selected backend type (str).
                - A boolean indicating whether the dialog was accepted (True) or canceled (False).
        """
        dialog = cls(application.main_window)
        result = dialog.exec_()

        return dialog.name_input.text(), dialog.backend_dropdown.currentText(), result == QtWidgets.QDialog.Accepted


    def build_layout(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.name_input)
        layout.addWidget(QtWidgets.QLabel("Select backend:", self))
        layout.addWidget(self.backend_dropdown)
        layout.addWidget(self.create_button, alignment=QtCore.Qt.AlignRight)
        self.setLayout(layout)

    def validate(self, text):
        if text in bd.databases or not text:
            self.create_button.setDisabled(True)
        else:
            self.create_button.setDisabled(False)


