from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal, SignalInstance


class LoginLayout(QtWidgets.QVBoxLayout):
    valid: SignalInstance = Signal(bool)
    invalid: SignalInstance = Signal(bool)

    def __init__(self,
                 label="",
                 warning="",
                 username_placeholder="Username",
                 username_preset="",
                 password_placeholder="Password",
                 password_preset="",
                 parent=None):
        super().__init__(parent)

        self.label = QtWidgets.QLabel(label)

        # Create warning text for when the user enters a database that already exists
        self.warning = QtWidgets.QLabel()
        self.warning.setTextFormat(QtCore.Qt.RichText)
        self.warning.setText(
            f"<p style='color: red; font-size: small;'>{warning}</p>")
        self.warning.setHidden(True)

        # Login fields
        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText(username_placeholder)
        self.username.setText(username_preset)

        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText(password_placeholder),
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setText(password_preset)

        # Validate when text is written
        self.username.textChanged.connect(self.validate)
        self.password.textChanged.connect(self.validate)

        self.addWidget(self.label)
        self.addWidget(self.username)
        self.addWidget(self.password)
        self.addWidget(self.warning)

    def validate(self) -> bool:
        if self.username.text() and self.password.text():
            self.valid.emit(True)
            self.invalid.emit(False)
            return True
        else:
            self.valid.emit(False)
            self.invalid.emit(True)
            return False
