from activity_browser import application
from activity_browser.actions.base import ABAction
from activity_browser.ui.wizards.db_import_wizard import DatabaseImportWizard
from activity_browser.ui.icons import qicons


class DatabaseImport(ABAction):
    icon = qicons.import_db
    title = "Import database..."
    tool_tip = "Import a new database"

    def onTrigger(self, toggled):
        wizard = DatabaseImportWizard(application.main_window)
        wizard.show()
