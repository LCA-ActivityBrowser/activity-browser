from PySide2 import QtWidgets
from PySide2.QtCore import Signal, SignalInstance


class LoginLayout(QtWidgets.QVBoxLayout):
    """
    Layout that contains username and password textboxes. Will check whether both are filled in and signal
    valid or invalid accordingly.
    """
    valid: SignalInstance = Signal(bool)
    invalid: SignalInstance = Signal(bool)

    def __init__(self,
                 label="",
                 username_placeholder="Username",
                 username_preset="",
                 password_placeholder="Password",
                 password_preset=""
                 ):
        """
        Parameters
        ----------
            label : `str`
                Header to show above the login screen. If an empty string is provided (default), label will not be added
            username_placeholder : `str`
                Text to show in the background of the username field
            username_preset : `str`
                Text with which to fill in the username field as suggestion
            password_placeholder : `str`
                Text to show in the background of the password field
            password_preset : `str`
                Text with which to fill in the password field as suggestion
        """
        super().__init__()

        self.label = QtWidgets.QLabel(label)

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

        if label:
            self.addWidget(self.label)
        self.addWidget(self.username)
        self.addWidget(self.password)

    def validate(self) -> bool:
        """
        Slot to validate whether the username and password are filled in and signal accordingly
        """
        if self.username.text() and self.password.text():
            self.valid.emit(True)
            self.invalid.emit(False)
            return True
        else:
            self.valid.emit(False)
            self.invalid.emit(True)
            return False
