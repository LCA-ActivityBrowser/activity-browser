from activity_browser.app.actions.base import ABAction, exception_dialogs

from activity_browser.ui.icons import qicons


class ManagePluginsOpen(ABAction):
    """Open Settings focused on the Plugins chapter."""

    icon = qicons.plugin
    text = "Manage plugins…"

    @staticmethod
    @exception_dialogs
    def run():
        from activity_browser.app.pages.settings import SettingsPage

        SettingsPage.open_chapter("Plugins")
