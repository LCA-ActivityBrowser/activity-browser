from loguru import logger

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.core.application import global_shortcut




class NodeSelectOpen(ABAction):

    icon = qicons.right
    text = "Open activity / activities"

    @staticmethod
    @global_shortcut("Ctrl+Shift+N")
    @exception_dialogs
    def run():
        from activity_browser.app import dialogs
        dialog = dialogs.NodeSelectDialog(parent=app.main_window)
        dialog.exec_()