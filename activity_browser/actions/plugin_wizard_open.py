from activity_browser import application
from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons
from activity_browser.ui.wizards.plugins_manager_wizard import PluginsManagerWizard


class PluginWizardOpen(NewABAction):
    """ABAction to open the PluginWizard"""
    icon = qicons.plugin
    text = "Plugin manager..."

    @staticmethod
    def run():
        PluginsManagerWizard(None, application.main_window).show()
