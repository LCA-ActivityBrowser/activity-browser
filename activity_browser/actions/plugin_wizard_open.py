from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.wizards.plugins_manager_wizard import PluginsManagerWizard


class PluginWizardOpen(ABAction):
    """ABAction to open the PluginWizard"""
    icon = qicons.plugin
    text = "Plugin manager..."

    @staticmethod
    @exception_dialogs
    def run():
        PluginsManagerWizard(None, application.main_window).show()
