# -*- coding: utf-8 -*-
import importlib.util
from pkgutil import iter_modules
from logging import getLogger

from qtpy.QtCore import QObject

from activity_browser import ab_settings, application, project_settings, signals
from activity_browser.mod import bw2data as bd

log = getLogger(__name__)


class PluginController(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.connect_signals()
        # Shortcut to ab_settings plugins list
        self.plugins = ab_settings.plugins
        self.import_plugins()

    def connect_signals(self):
        signals.project.changed.connect(self.reload_plugins)
        signals.plugin_selected.connect(self.load_plugin)

    def import_plugins(self):
        """Import plugins from python environment."""
        names = self.discover_plugins()
        for name in names:
            plugin = self.import_plugin(name)
            if plugin:
               self.plugins[name] = plugin

    def discover_plugins(self):
        """Discover available plugins in python environment."""
        plugins = []
        for module in iter_modules():
            if module.name.startswith("ab_plugin"):
                plugins.append(module.name)
        return plugins

    def import_plugin(self, name):
        """Import plugin from python environment."""
        try:
            log.info("Importing plugin {}".format(name))
            plugin_lib = importlib.import_module(name)
            importlib.reload(plugin_lib)
            return plugin_lib.Plugin()
        except Exception as e:
            log.error(f"Import of plugin module '{name}' failed. "
                      "If this keeps happening contact the plugin developers and let them know of this error:"
                      f"\n{e}")
            return None

    def load_plugin(self, name, select: bool = True):
        """Load or unload the Plugin, depending on select."""
        if select:
            # load the plugin
            plugin = self.plugins[name]
            # Apply plugin load() function
            try:
                plugin.load()
            except Exception as e:
                log.warning(f"Failed to load plugin '{name}' due to an error in the plugin, ignoring plugin. "
                            "If this keeps happening contact the plugin developers and let them know of this error:"
                            f"\n{e}")
                return

            # Add plugins tabs
            for tab in plugin.tabs:
                application.main_window.add_tab_to_panel(
                    tab, plugin.infos["name"], tab.panel
                )
            log.info(f"Loaded tab '{name}'")
            return

        # not select, remove the plugin
        log.info(f"Removing plugin '{name}'")

        self.close_plugin_tabs(self.plugins[name])  # close tabs in AB
        self.plugins[name].close()  # call close of the plugin
        self.plugins[name].remove()  # call remove of the plugin

    def close_plugin_tabs(self, plugin):
        for panel in (
            application.main_window.left_panel,
            application.main_window.right_panel,
        ):
            panel.close_tab_by_tab_name(plugin.infos["name"])

    def reload_plugins(self):
        """close all plugins then reload all plugins."""
        plugins_list = [name for name in self.plugins.keys()]  # copy plugins list
        for name in plugins_list:
            self.close_plugin_tabs(self.plugins[name])  # close tabs in AB
            self.plugins[name].close()  # call close of the plugin
        for name in project_settings.get_plugins_list():
            if name in self.plugins:
                self.load_plugin(name)
            else:
                log.warning(f"Reloading of plugin '{name}' was skipped due to a previous error. "
                            "To reload this plugin, restart Activity Browser")

    def close(self):
        """Close all plugins, called when AB closes."""
        for plugin in self.plugins.values():
            plugin.close()


plugin_controller = PluginController(application)
