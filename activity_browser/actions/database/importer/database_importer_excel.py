from logging import getLogger

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal, SignalInstance

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.mod.tqdm import qt_tqdm
from activity_browser.mod.pyprind import qt_pyprind
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread
from activity_browser.ui.widgets import ABProgressDialog
from activity_browser.bwutils.importers import ABExcelImporter

log = getLogger(__name__)


class DatabaseImporterExcel(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = qicons.import_db
    text = "Import database from brightway excel format"
    tool_tip = "Import database from brightway excel format"

    @classmethod
    @exception_dialogs
    def run(cls):
        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=application.main_window,
            caption='Choose brightway excel database to import',
            filter='excel spreadsheet (*.xlsx);; All files (*.*)'
        )
        if not path:
            return

        # initialize the import thread, setting needed attributes
        extract_thread = ExtractExcelThread(application)
        extract_thread.path = path
        extract_thread.loaded.connect(cls.write_database)
        extract_thread.start()

    @staticmethod
    def write_database(importer: ABExcelImporter):
        # show the import setup dialog
        import_dialog = ImportSetupDialog(importer, application.main_window)
        if import_dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        # setup the importer thread
        importer_thread = ImportExcelThread(application)
        importer_thread.importer = importer
        importer_thread.database_name = import_dialog.database_name
        importer_thread.linking_dict = import_dialog.linking_dict

        # setup a progress dialog
        progress_dialog = ABProgressDialog.get_connected_dialog("Importing Database")
        importer_thread.finished.connect(progress_dialog.deleteLater)

        progress_dialog.show()
        importer_thread.start()


class ImportSetupDialog(QtWidgets.QDialog):
    database_name = None
    linking_dict = None

    def __init__(self, importer: ABExcelImporter, parent=None):
        super().__init__(parent)
        self.importer = importer

        self.setWindowTitle("Import database from Excel")

        # Create db name textbox
        self.db_name_textbox = QtWidgets.QLineEdit()
        self.db_name_textbox.setPlaceholderText("Database name")
        self.db_name_textbox.setText(importer.db_name)
        self.db_name_textbox.textChanged.connect(self.db_name_check)

        # Create warning text for when the user enters a database that already exists
        self.db_name_warning = QtWidgets.QLabel()
        self.db_name_warning.setTextFormat(QtCore.Qt.RichText)
        self.db_name_warning.setText(
            "<p style='color: red; font-size: small;'>Existing database will be overwritten</p>")
        self.db_name_warning.setHidden(True)

        # Create OK and Cancel buttons
        self.ok_button = QtWidgets.QPushButton("OK")
        self.cancel_button = QtWidgets.QPushButton("Cancel")

        self.ok_button.setEnabled(False)

        # Connect buttons to their respective slots
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Set button layout
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        # Create layout and add widgets
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Set database name:"))
        layout.addWidget(self.db_name_textbox)
        layout.addWidget(self.db_name_warning)
        layout.addLayout(self.get_linking_layout())
        layout.addLayout(button_layout)

        # Set the dialog layout
        self.setLayout(layout)
        self.validate()

    def get_linking_layout(self):
        # extract all the databases from the importer
        other_dbs = set()
        for act in self.importer.data:
            for exc in act["exchanges"]:
                other_dbs.add(exc["database"])
        other_dbs.discard(self.importer.db_name)

        # setup the layout
        layout = QtWidgets.QGridLayout()

        # return empty layout if there's nothing to link
        if not other_dbs:
            return layout

        # add the header
        layout.addWidget(QtWidgets.QLabel("Link databases:"), 0, 0)

        # for each "other db" create a label naming the db and a drop-down of db's to choose from
        for i, db in enumerate(other_dbs):
            # create a combobox, set the db_name as combobox.orignal_db
            combo = QtWidgets.QComboBox(self)
            combo.addItems(bd.databases)
            combo.currentIndexChanged.connect(self.validate)  # validate whenever the combobox changes
            setattr(combo, "original_db", db)  # needed to build the linking dictionary

            # set the combobox to a db with the same name if it exists
            if db in bd.databases:
                combo.setCurrentIndex(list(bd.databases).index(db))
            # else set the combobox to empty
            else:
                combo.setCurrentIndex(-1)

            # add label and combobox next to eachother to the gridlayout
            layout.addWidget(QtWidgets.QLabel(db, self), i + 1, 0, 1, 2)
            layout.addWidget(combo, i + 1, 2, 1, 2)

        return layout

    def db_name_check(self):
        """Slot for when the db_name_textbox is changed, hide/show the warning and validate"""
        if self.db_name_textbox.text() in bd.databases:
            self.db_name_warning.setHidden(False)
        else:
            self.db_name_warning.setHidden(True)
        self.window().adjustSize()
        self.validate()

    def build_linking_dict(self) -> dict[str, str]:
        linking_dict = {}
        for child in self.findChildren(QtWidgets.QComboBox):
            linking_dict[child.original_db] = child.currentText()
        return linking_dict

    def validate(self):
        """Validate the user input and enable the OK button if all is clear"""
        valid = (
                bool(self.db_name_textbox.text())  # the textbox has been filled in
                and not [i for i in self.build_linking_dict().values() if i == ""]  # no link dropdowns are empty
        )
        self.ok_button.setEnabled(valid)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.db_name_textbox.text()
        self.linking_dict = self.build_linking_dict()
        super().accept()


class ExtractExcelThread(ABThread):
    loaded: SignalInstance = Signal(ABExcelImporter)
    path = None

    def run_safely(self):
        importer = ABExcelImporter(self.path)
        self.loaded.emit(importer)


class ImportExcelThread(ABThread):
    database_name: str
    linking_dict: dict[str, str]
    importer: ABExcelImporter

    def run_safely(self):
        self.importer.automated_import(self.database_name, self.linking_dict)

