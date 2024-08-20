from PySide2 import QtWidgets, QtCore
import activity_browser.mod.bw2data as bd


class DatabaseNameLayout(QtWidgets.QVBoxLayout):
    def __init__(self,
                 label: str | None = "Set database name",
                 database_placeholder="Database name",
                 database_preset="",
                 overwrite_warning="Existing database will be overwritten",
                 parent=None):
        super().__init__(parent)

        self.label = QtWidgets.QLabel(label)

        # Create db name textbox
        self.database_name = QtWidgets.QLineEdit()
        self.database_name.setPlaceholderText(database_placeholder)
        self.database_name.setText(database_preset)

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
        if self.database_name.text() in bd.databases:
            self.warning.setHidden(False)
        else:
            self.warning.setHidden(True)
