from activity_browser import application
from .base import ABAction
from ..ui.icons import qicons
from ..ui.wizards.settings_wizard import SettingsWizard


class SettingsWizardOpen(ABAction):
    """ABAction to open the SettingsWizard"""
    icon = qicons.settings
    title = "Settings..."
    wizard: SettingsWizard

    def onTrigger(self, toggled):
        self.wizard = SettingsWizard(application.main_window)
        self.wizard.show()
