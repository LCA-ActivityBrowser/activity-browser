from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.wizards.db_export_wizard import DatabaseExportWizard


class DatabaseExport(ABAction):
    """
    ABAction to open the DatabaseExportWizard.
    """

    icon = application.style().standardIcon(QtWidgets.QStyle.SP_DriveHDIcon)
    text = "Export database..."
    tool_tip = "Export a database from this project"

    @staticmethod
    @exception_dialogs
    def run():
        DatabaseExportWizard(application.main_window).show()
