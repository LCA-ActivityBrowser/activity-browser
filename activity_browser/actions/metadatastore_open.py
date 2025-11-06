from loguru import logger

from activity_browser import app
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.core.application import global_shortcut




class MetaDataStoreOpen(ABAction):

    icon = qicons.right
    text = "Open activity / activities"

    @staticmethod
    @global_shortcut("Ctrl+Shift+M")
    @exception_dialogs
    def run():
        from activity_browser.app import pages
        page = pages.MetaDataStorePage()
        central = app.main_window.centralWidget()
        central.addToGroup("DEBUG", page)
