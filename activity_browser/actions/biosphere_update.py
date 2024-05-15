from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.widgets import BiosphereUpdater, EcoinventVersionDialog
from activity_browser.utils import sort_semantic_versions
from activity_browser.info import __ei_versions__


class BiosphereUpdate(ABAction):
    """
    ABAction to open the Biosphere updater.
    """
    icon = application.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
    text = "Update biosphere..."

    @staticmethod
    @exception_dialogs
    def run():
        """ Open a popup with progression bar and run through the different
        functions for adding ecoinvent biosphere flows.
        """
        # warn user of consequences of updating
        warn_dialog = QtWidgets.QMessageBox.question(
            application.main_window, "Update biosphere3?",
            'Newer versions of the biosphere database may not\n'
            'always be compatible with older ecoinvent versions.\n'
            '\nUpdating the biosphere3 database cannot be undone!\n',
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Abort,
            QtWidgets.QMessageBox.Abort
        )
        if warn_dialog is not QtWidgets.QMessageBox.Ok: return

        # let user choose version
        version_dialog = EcoinventVersionDialog(application.main_window)
        if version_dialog.exec_() != EcoinventVersionDialog.Accepted: return
        version = version_dialog.options.currentText()

        # reduce biosphere update list up to the selected version
        sorted_versions = sort_semantic_versions(__ei_versions__, highest_to_lowest=False)
        ei_versions = sorted_versions[:sorted_versions.index(version) + 1]

        # show updating dialog
        BiosphereUpdater(ei_versions, application.main_window).show()
