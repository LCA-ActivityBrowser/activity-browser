import os

from bw2data.parameters import Group
from qtpy import QtCore, QtWidgets

from activity_browser import application, project_settings
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from bw2data.backends.proxies import (ExchangeDataset,
                                                           Exchanges)
from activity_browser.ui.icons import qicons
from activity_browser.layouts.panes import DatabaseExplorer


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
        db_explorer = DatabaseExplorer(db_name, application.main_window)
        db_explorer.show()
