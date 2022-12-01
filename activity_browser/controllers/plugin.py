# -*- coding: utf-8 -*-
import sys
import importlib.util
import traceback
from shutil import rmtree

from PySide2.QtCore import QObject, Slot

from ..ui.wizards.plugin_import_wizard import PluginImportWizard
from ..signals import signals
from ..settings import project_settings, ab_settings


class PluginController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent
        # Currently loaded plugins objects as:
        # {plugin_name: <plugin_object>, ...}
        self.plugins = {}

        self.connect_signals()

    def connect_signals(self):
        signals.import_plugin.connect(self.import_plugin_wizard)
        signals.project_selected.connect(self.reload_plugins)
        signals.plugin_selected.connect(self.add_plugin)
        signals.plugin_deselected.connect(self.remove_plugin)
        signals.delete_plugin.connect(self.delete_plugin)

    @Slot(name="openImportWizard")
    def import_plugin_wizard(self) -> None:
        """Start the plugin importation wizard."""
        wizard = PluginImportWizard(self.window)
        wizard.show()
    
    def import_plugin(self, name):
        """ load given plugin package and return Plugin instance
        """
        try:
            print("Loading plugin {}".format(name))
            plugins_dir = ab_settings.plugins_dir
            plugin_lib = importlib.import_module(name, plugins_dir)
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
        self.close_plugin_tabs(name)
        # Remove plugin object from plugins dict
        del self.plugins[name]

    def add_plugin(self, name):
        """ add or reload tabs of the given plugin
        """
        # Create plugin object
        plugin = self.import_plugin(name)
        # Apply pluin load() function
        plugin.load()
        # Add plugin object to plugin dict
        self.plugins[name] = plugin
        # Add plugins tabs
        for tab in plugin.tabs:
            self.window.add_tab_to_panel(tab, plugin.infos["name"], tab.panel)

    def delete_plugin(self, name):
        print("Deleting plugin {}".format(name))
        if name in self.plugins.keys():
            self.remove_plugin(name)
        plugin_path = "{}/{}".format(ab_settings.plugins_dir, name)
        rmtree(plugin_path)

    def close_plugin_tabs(self, plugin):
        for panel in (self.window.left_panel, self.window.right_panel):
            panel.close_tab_by_tab_name(plugin)

    def reload_plugins(self):
        """ close all plugins tabs then import all plugins tabs
        """
        plugins_list = [name for name in self.plugins.keys()]   # copy plugins list
        for name in plugins_list:
            self.remove_plugin(name)
        sys.path.append(ab_settings.plugins_dir)
        for name in project_settings.get_plugins_list():
            self.add_plugin(name)

    def close_plugins(self):
        for plugin in self.plugins.values():
            plugin.close()