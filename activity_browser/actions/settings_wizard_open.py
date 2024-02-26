from activity_browser import application
from .base import ABAction
from ..ui.icons import qicons
from ..ui.wizards.settings_wizard import SettingsWizard


class SettingsWizardOpen(ABAction):
    icon = qicons.settings
    title = "Settings..."

    def onTrigger(self, toggled):
        wizard = SettingsWizard(application.main_window)
        wizard.show()
