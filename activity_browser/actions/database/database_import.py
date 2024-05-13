from activity_browser import application
from activity_browser.actions.base import NewABAction
from activity_browser.ui.wizards.db_import_wizard import DatabaseImportWizard
from activity_browser.ui.icons import qicons


class DatabaseImport(NewABAction):
    """ABAction to open the DatabaseImportWizard"""
    icon = qicons.import_db
    text = "Import database..."
    tool_tip = "Import a new database"

    @staticmethod
    def run():
        DatabaseImportWizard(application.main_window).show()
