from PySide2 import QtWidgets, QtCore
import activity_browser.mod.bw2data as bd


class DatabaseNameLayout(QtWidgets.QVBoxLayout):
    """
    Simple LineEdit layout that will check whether the database name provided by the user already exist and warn
    the user accordingly.
    """

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

        # Only show warning when a string is given
        if overwrite_warning:
            self.database_name.textChanged.connect(self.name_check)

        # Create warning text for when the user enters a database that already exists
        self.warning = QtWidgets.QLabel()
        self.warning.setTextFormat(QtCore.Qt.RichText)
        self.warning.setText(
            f"<p style='color: red; font-size: small;'>{overwrite_warning}</p>")
        self.warning.setHidden(True)

        if label:
            self.addWidget(self.label)
        self.addWidget(self.database_name)
        self.addWidget(self.warning)

    def name_check(self):
        """Slot to check whether the database already exists and show the warning if so"""
        if self.database_name.text() in bd.databases:
            self.warning.setHidden(False)
        else:
            self.warning.setHidden(True)
