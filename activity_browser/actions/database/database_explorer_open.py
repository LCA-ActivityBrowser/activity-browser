from activity_browser import app
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class DatabaseExplorerOpen(ABAction):
    """
    ABAction to delete a database from the project. Asks the user for confirmation. If confirmed, instructs the
    DatabaseController to delete the database in question.
    """

    icon = qicons.delete
    text = "Explore database"
    tool_tip = "Delete this database from the project"

    @staticmethod
    @exception_dialogs
    def run(db_name: str):
        from activity_browser.app.panes import DatabaseExplorerPane
        db_explorer = DatabaseExplorerPane(db_name, app.main_window)
        db_explorer.show()
