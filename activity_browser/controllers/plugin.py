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
        signals.plugin_deselected.connect(self.remove_plugin)

    @Slot(name="openManagerWizard")
    def manage_plugins_wizard(self) -> None:
        wizard = PluginsManagerWizard(self.window)
        wizard.show()

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
            print("Loading plugin {}".format(name))
            plugin_lib = importlib.import_module(name)
            importlib.reload(plugin_lib)
            return plugin_lib.Plugin()
        except:
            print("Error: Import of plugin {} failed".format(name))
            print(traceback.format_exc())

    def remove_plugin(self, name):
        print("Removing plugin {}".format(name))
        # Apply plugin remove() function
        self.plugins[name].remove()
        # Close plugin tabs
        self.close_plugin_tabs(self.plugins[name])

    def add_plugin(self, name):
        """ add or reload tabs of the given plugin
        """
        plugin = self.plugins[name]
        # Apply pluin load() function
        plugin.load()
        # Add plugins tabs
        for tab in plugin.tabs:
            self.window.add_tab_to_panel(tab, plugin.infos["name"], tab.panel)

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
                print(f"Error: plugin {name} not installed")

    def close_plugins(self):
        """ close all plugins
        """
        for plugin in self.plugins.values():
            plugin.close()