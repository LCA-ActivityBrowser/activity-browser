# -*- coding: utf-8 -*-
import sys
import importlib.util
import traceback
from pkgutil import iter_modules
from shutil import rmtree

from PySide2.QtCore import QObject, Slot

from ..ui.wizards.plugins_manager_wizard import PluginsManagerWizard
from ..signals import signals
from ..settings import project_settings, ab_settings

import logging
from activity_browser.logger import ABHandler

logger = logging.getLogger('ab_logs')
log = ABHandler.setup_with_logger(logger, __name__)


class PluginController(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent
        self.connect_signals()
        # Shortcut to ab_settings plugins list
        self.plugins = ab_settings.plugins
        self.load_plugins()

    def connect_signals(self):
        signals.manage_plugins.connect(self.manage_plugins_wizard)
        signals.project_selected.connect(self.reload_plugins)
        signals.plugin_selected.connect(self.add_plugin)

    @Slot(name="openManagerWizard")
    def manage_plugins_wizard(self) -> None:
        self.wizard = PluginsManagerWizard(self.window)
        self.wizard.show()

    def load_plugins(self):
        names = self.discover_plugins()
        for name in names:
            self.plugins[name] = self.load_plugin(name)

    def discover_plugins(self):
        plugins = []
        for module in iter_modules():
            if module.name.startswith('ab_plugin'):
                plugins.append(module.name)
        return plugins

    def load_plugin(self, name):
        try:
            log.info("Importing plugin {}".format(name))
            plugin_lib = importlib.import_module(name)
            importlib.reload(plugin_lib)
            return plugin_lib.Plugin()
        except Exception as e:
            log.error("Error: Import of plugin {} failed".format(name), error=e)

    def add_plugin(self, name, select: bool = True):
        """ add or reload tabs of the given plugin
        """
        if select:
            plugin = self.plugins[name]
            # Apply plugin load() function
            plugin.load()
            # Add plugins tabs
            for tab in plugin.tabs:
                self.window.add_tab_to_panel(tab, plugin.infos["name"], tab.panel)
            log.info("Loaded tab {}".format(name))
            return
        log.info("Removing plugin {}".format(name))
        # Apply plugin remove() function
        self.plugins[name].remove()
        # Close plugin tabs
        self.close_plugin_tabs(self.plugins[name])

    def close_plugin_tabs(self, plugin):
        for panel in (self.window.left_panel, self.window.right_panel):
            panel.close_tab_by_tab_name(plugin.infos["name"])

    def reload_plugins(self):
        """ close all plugins tabs then import all plugins tabs
        """
        plugins_list = [name for name in self.plugins.keys()]   # copy plugins list
        for name in plugins_list:
            self.close_plugin_tabs(self.plugins[name])
        for name in project_settings.get_plugins_list():
            try:
                self.add_plugin(name)
            except:
                log.error(f"Error: plugin {name} not installed")

    def close_plugins(self):
        """ close all plugins
        """
        for plugin in self.plugins.values():
            plugin.close()
