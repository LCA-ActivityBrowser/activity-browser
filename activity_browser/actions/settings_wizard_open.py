from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.wizards.settings_wizard import SettingsWizard


class SettingsWizardOpen(ABAction):
    """ABAction to open the SettingsWizard"""

    icon = qicons.settings
    text = "Settings..."

    @staticmethod
    @exception_dialogs
    def run():
        SettingsWizard(application.main_window).show()
