from activity_browser import application
from .base import ABAction
from ..ui.wizards.db_import_wizard import DatabaseImportWizard
from ..ui.icons import qicons


class DatabaseImport(ABAction):
    icon = qicons.import_db
    title = "Import database..."
    tool_tip = "Import a new database"

    def onTrigger(self, toggled):
        wizard = DatabaseImportWizard(application.main_window)
        wizard.show()
