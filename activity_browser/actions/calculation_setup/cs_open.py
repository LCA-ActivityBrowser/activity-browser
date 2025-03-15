from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class CSOpen(ABAction):
    """
    ABAction to create a new Calculation Setup. Prompts the user for a name for the new CS. Returns if the user cancels,
    or when a CS with the same name is already present within the project. Otherwise, instructs the CSController to
    create a new Calculation Setup with the given name.
    """

    icon = qicons.add
    text = "New"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str):
        tab = application.main_window.right_panel.tabs["LCA Setup"]
        tab.open_cs(cs_name)

