from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd


class DatabaseSetReadonly(ABAction):
    """
    ABAction to set a database as read-only.

    This action allows marking a database as read-only by updating its metadata.
    It can also be used to remove the read-only status by setting the `read_only` flag to `False`.

    Attributes:
        text (str): The display text for this action.
        tool_tip (str): The tooltip text for this action.
    """

    text = "Set database read-only"
    tool_tip = "Set this database to read-only"

    @staticmethod
    @exception_dialogs
    def run(db_name: str, read_only=True):
        """
        Execute the action to set the read-only status of a database.

        This method updates the `read_only` flag in the metadata of the specified database.

        Args:
            db_name (str): The name of the database to update.
            read_only (bool, optional): The desired read-only status. Defaults to True.
        """
        bd.databases[db_name]["read_only"] = read_only
        bd.databases.flush()
