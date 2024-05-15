from activity_browser import application
from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons
from activity_browser.ui.wizards.settings_wizard import SettingsWizard


class SettingsWizardOpen(NewABAction):
    """ABAction to open the SettingsWizard"""
    icon = qicons.settings
    text = "Settings..."

    @staticmethod
    def run():
        SettingsWizard(application.main_window).show()
