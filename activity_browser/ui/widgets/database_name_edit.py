from qtpy import QtWidgets, QtCore

import bw2data as bd


class DatabaseNameEdit(QtWidgets.QWidget):
    """
    Extended LineEdit widget that will check whether the database name provided by the user already exist and warn
    the user accordingly.
    """
    textChanged: QtCore.SignalInstance = QtCore.Signal(str)

    def __init__(self,
                 label: str | None = "",
                 database_placeholder="Database name",
                 database_preset="",
                 overwrite_warning="Existing database will be overwritten",
                 ):
        """
        Parameters
        ----------
            label : `str`
                Header to show above the text field. If an empty string is provided (default), label will not be added
            database_placeholder : `str`
                Text to show in the background of the database field
            database_preset : `str`
                Text with which to fill in the database field as suggestion
            overwrite_warning : `str`
                Text to show as warning when the database already exists. If the string is empty, no warning will be
                shown
        """
        super().__init__()

        self.label = QtWidgets.QLabel(label)

        # Create db name textbox
        self.database_name = QtWidgets.QLineEdit()
        self.database_name.setPlaceholderText(database_placeholder)
        self.database_name.setText(database_preset)
        self.database_name.textChanged.connect(self.textChanged.emit)

        # Only show warning when a string is given
        if overwrite_warning:
            self.database_name.textChanged.connect(self._update)

        # Create warning text for when the user enters a database that already exists
        self.warning = QtWidgets.QLabel()
        self.warning.setTextFormat(QtCore.Qt.RichText)
        self.warning.setText(
            f"<p style='color: red; font-size: small;'>{overwrite_warning}</p>")
        self.warning.setHidden(True)

        layout = QtWidgets.QVBoxLayout()

        if label:
            layout.addWidget(self.label)
        layout.addWidget(self.database_name)
        layout.addWidget(self.warning)

        self.setLayout(layout)

    def _update(self):
        """Slot to check whether the database already exists and show the warning if so"""
        if self.willOverwrite():
            self.warning.setHidden(False)
        else:
            self.warning.setHidden(True)

    def text(self) -> str:
        return self.database_name.text()

    def setText(self, text: str):
        self.database_name.setText(text)

    def willOverwrite(self) -> bool:
        return self.database_name.text() in bd.databases

