from logging import getLogger

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import icons, threading, widgets
from activity_browser.bwutils.io.ecoinvent_lcia_importer import EcoinventLCIAImporter

log = getLogger(__name__)


class MethodImporterEcoinvent(ABAction):
    """ABAction to import methods from ecoinvent"""

    icon = icons.qicons.import_db
    text = "Import methods from ecoinvent excel format"
    tool_tip = "Import methods from ecoinvent excel format"

    @classmethod
    @exception_dialogs
    def run(cls):
        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=application.main_window,
            caption='Choose ecoinvent methods excel to import',
            filter='excel spreadsheet (*.xlsx);; All files (*.*)'
        )
        if not path:
            return

        # initialize the import thread, setting needed attributes
        extract_thread = ExtractExcelThread(application)
        extract_thread.path = path
        extract_thread.loaded.connect(cls.write_database)

        # show progress dialog for importing the excel
        progress_dialog = widgets.ABProgressDialog.get_connected_dialog("Importing Database")
        extract_thread.finished.connect(progress_dialog.deleteLater)

        extract_thread.start()

    @staticmethod
    def write_database(importer: EcoinventLCIAImporter):
        # show the import setup dialog
        import_dialog = ImportSetupDialog(importer, application.main_window)
        if import_dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        # setup the importer thread
        importer_thread = ImportExcelThread(application)
        importer_thread.importer = importer
        importer_thread.biosphere_name = import_dialog.biosphere_name
        importer_thread.prepend = import_dialog.prepend

        # setup a progress dialog
        progress_dialog = widgets.ABProgressDialog.get_connected_dialog("Importing Impact Categories")
        importer_thread.finished.connect(progress_dialog.deleteLater)

        progress_dialog.show()
        importer_thread.start()


class ImportSetupDialog(QtWidgets.QDialog):
    biosphere_name: str
    prepend: str

    def __init__(self, importer: EcoinventLCIAImporter, parent=None):
        super().__init__(parent)
        self.importer = importer

        self.setWindowTitle("Import methods from ecoinvent Excel")

        self.db_chooser = widgets.ABComboBox.get_database_combobox(self)
        self.button_comp = composites.HorizontalButtonsComposite("Cancel", "*OK")

        self.info = QtWidgets.QLabel()
        self.info.setWordWrap(True)
        self.info.setTextFormat(QtCore.Qt.RichText)

        self.prepend_label = QtWidgets.QLabel("Prepend method names")

        self.prepend_textbox = QtWidgets.QLineEdit()
        self.prepend_textbox.setPlaceholderText("Enter name prepend")
        self.prepend_textbox.textChanged.connect(self.check_overwrite)

        # Connect the necessary signals
        self.button_comp["OK"].clicked.connect(self.accept)
        self.button_comp["Cancel"].clicked.connect(self.reject)

        # Create final layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Choose biosphere database:"))
        layout.addWidget(self.db_chooser)
        layout.addWidget(self.prepend_label)
        layout.addWidget(self.prepend_textbox)
        layout.addWidget(self.info)
        layout.addWidget(self.button_comp)

        # Set the dialog layout
        self.setLayout(layout)
        self.validate()
        self.check_overwrite()

    def check_overwrite(self, prepend=None) -> int:
        overwrite = 0
        for name in [x["name"] for x in self.importer.data]:
            if prepend:
                name = tuple([prepend, *name])

            if name in bd.methods:
                overwrite += 1

        if not overwrite:
            self.info.setText("")
            return overwrite

        self.info.setText(
            f"<p style='color: red; font-size: small;'>This action will overwrite {overwrite} impact categories</p>"
        )

        return overwrite

    def validate(self):
        """Validate the user input and enable the OK button if all is clear"""
        valid = True
        self.button_comp["OK"].setEnabled(valid)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.biosphere_name = self.db_chooser.currentText()
        self.prepend = self.prepend_textbox.text()
        super().accept()


class ExtractExcelThread(threading.ABThread):
    loaded: SignalInstance = Signal(EcoinventLCIAImporter)
    path: str

    def run_safely(self):
        importer = EcoinventLCIAImporter.setup_with_ei_excel(self.path)
        self.loaded.emit(importer)


class ImportExcelThread(threading.ABThread):
    biosphere_name: str
    prepend: str
    importer: EcoinventLCIAImporter

    def run_safely(self):
        self.importer.set_biosphere(self.biosphere_name)
        self.importer.apply_strategies()
        self.importer.prepend_methods(self.prepend)
        self.importer.write_methods(overwrite=True)

