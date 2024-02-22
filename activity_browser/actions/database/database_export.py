from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction
from activity_browser.ui.wizards.db_export_wizard import DatabaseExportWizard


class DatabaseExport(ABAction):
    icon = application.style().standardIcon(QtWidgets.QStyle.SP_DriveHDIcon)
    title = "Export database..."
    tool_tip = "Export a database from this project"

    def onTrigger(self, toggled):
        wizard = DatabaseExportWizard(application.main_window)
        wizard.show()
