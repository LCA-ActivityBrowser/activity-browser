from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class DatabaseProcess(ABAction):
    """
    ...
    """

    icon = qicons.process
    text = "Process database"
    tool_tip = "Process database into datapackages"

    @staticmethod
    @exception_dialogs
    def run(db_name: str):
        db = bd.Database(db_name)
        db.process()
