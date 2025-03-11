import os.path
from logging import getLogger

from qtpy.QtCore import Signal, SignalInstance

from activity_browser import application
from activity_browser.actions.base import exception_dialogs
from activity_browser.ui import icons, widgets, threading
from activity_browser.bwutils.io.ecoinvent_lcia_importer import EcoinventLCIAImporter

from .method_importer_ecoinvent import ExtractExcelThread, MethodImporterEcoinvent

log = getLogger(__name__)


class MethodImporterBW2IO(MethodImporterEcoinvent):
    """ABAction to import ecoinvent methods shipped with BW2IO"""

    icon = icons.qicons.import_db
    text = "Import methods from BW2IO"
    tool_tip = "Import methods that come shipped with BW2IO"

    @classmethod
    @exception_dialogs
    def run(cls):
        # initialize the import thread, setting needed attributes
        extract_thread = ExtractMethodsThread(application)
        extract_thread.loaded.connect(cls.write_database)

        # show progress dialog for importing the excel
        progress_dialog = widgets.ABProgressDialog.get_connected_dialog("Importing Database")
        extract_thread.finished.connect(progress_dialog.deleteLater)

        extract_thread.start()


class ExtractMethodsThread(threading.ABThread):
    loaded: SignalInstance = Signal(EcoinventLCIAImporter)

    def run_safely(self):
        import zipfile
        import json
        from bw2io.data import dirpath

        fp = os.path.join(dirpath, "lcia", "lcia_39_ecoinvent.zip")

        with zipfile.ZipFile(fp, mode="r") as archive:
            data = json.load(archive.open("data.json"))

        for method in data:
            method['name'] = tuple(method['name'])
            for obj in method['exchanges']:
                del obj['input']

        ei = EcoinventLCIAImporter("lcia_39_ecoinvent.zip")
        ei.data = data
        self.loaded.emit(ei)

