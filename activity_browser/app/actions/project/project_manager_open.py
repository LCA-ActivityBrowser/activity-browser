from activity_browser.app.actions.base import ABAction, exception_dialogs

from activity_browser.ui.icons import qicons


class ProjectManagerOpen(ABAction):
    """Open Settings focused on the Projects chapter."""

    icon = qicons.settings
    text = "Manage projects"

    @staticmethod
    @exception_dialogs
    def run():
        from activity_browser.app.pages.settings import SettingsPage

        SettingsPage.open_chapter("Projects")
