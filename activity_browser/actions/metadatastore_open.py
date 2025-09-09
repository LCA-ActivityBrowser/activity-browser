from logging import getLogger

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets.main_window import global_shortcut

log = getLogger(__name__)


class MetaDataStoreOpen(ABAction):

    icon = qicons.right
    text = "Open activity / activities"

    @staticmethod
    @global_shortcut("Ctrl+Shift+M")
    @exception_dialogs
    def run():
        from activity_browser.layouts import pages
        print("Running MetaDataStoreOpen action")

        # Create a details page for the activity
        page = pages.MetaDataStorePage()
        central = application.main_window.centralWidget()

        # Add the details page to the "Activity Details" group in the central widget
        central.addToGroup("DEBUG", page)
