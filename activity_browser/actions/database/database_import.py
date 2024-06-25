from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.wizards.db_import_wizard import DatabaseImportWizard


class DatabaseImport(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = qicons.import_db
    text = "Import database..."
    tool_tip = "Import a new database"

    @staticmethod
    @exception_dialogs
    def run():
        DatabaseImportWizard(application.main_window).show()
