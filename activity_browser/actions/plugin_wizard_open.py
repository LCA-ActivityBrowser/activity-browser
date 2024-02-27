from activity_browser import application
from .base import ABAction
from ..ui.icons import qicons
from ..ui.wizards.plugins_manager_wizard import PluginsManagerWizard


class PluginWizardOpen(ABAction):
    """ABAction to open the PluginWizard"""
    icon = qicons.plugin
    title = "Plugin manager..."

    def onTrigger(self, toggled):
        wizard = PluginsManagerWizard(application.main_window)
        wizard.show()
