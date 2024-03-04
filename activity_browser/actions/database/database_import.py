from activity_browser import application
from activity_browser.actions.base import ABAction
from activity_browser.ui.wizards.db_import_wizard import DatabaseImportWizard
from activity_browser.ui.icons import qicons


class DatabaseImport(ABAction):
    """ABAction to open the DatabaseImportWizard"""
    icon = qicons.import_db
    title = "Import database..."
    tool_tip = "Import a new database"
    wizard: DatabaseImportWizard

    def onTrigger(self, toggled):
        self.wizard = DatabaseImportWizard(application.main_window)
        self.wizard.show()
