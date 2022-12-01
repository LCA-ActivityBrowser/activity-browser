# -*- coding: utf-8 -*-
import json
import os
import sys
from pathlib import Path
from shutil import rmtree
import shutil
import importlib
from typing import Optional

import appdirs
import brightway2 as bw

from .signals import signals


class BaseSettings(object):
    """ Base Class for handling JSON settings files.
    """
    def __init__(self, directory: str, filename: str = None):
        self.data_dir = directory
        self.filename = filename or "default_settings.json"
        self.settings_file = os.path.join(self.data_dir, self.filename)
        self.settings: Optional[dict] = None
        self.initialize_settings()

    @classmethod
    def get_default_settings(cls) -> dict:
        """ Returns dictionary containing the default settings for the file
        """
        raise NotImplementedError

    def restore_default_settings(self) -> None:
        """ Undo all user settings and return to original state.
        """
        self.settings = self.get_default_settings()
        self.write_settings()

    def initialize_settings(self) -> None:
        """ Attempt to find and read the settings_file, creates a default
        if not found
        """
        if os.path.isfile(self.settings_file):
            self.load_settings()
        else:
            self.settings = self.get_default_settings()
            self.write_settings()

    def load_settings(self) -> None:
        with open(self.settings_file, "r") as infile:
            self.settings = json.load(infile)

    def write_settings(self) -> None:
        with open(self.settings_file, "w") as outfile:
            json.dump(self.settings, outfile, indent=4, sort_keys=True)


class ABSettings(BaseSettings):
    """
    Interface to the json settings file. Will create a userdata directory via appdirs if not
    already present.
    """
    def __init__(self, filename: str):
        ab_dir = appdirs.AppDirs("ActivityBrowser", "ActivityBrowser")
        self.plugins_dir = os.path.join(ab_dir.user_data_dir, "plugins")

        if not os.path.isdir(ab_dir.user_data_dir):
            os.makedirs(ab_dir.user_data_dir, exist_ok=True)
        self.move_old_settings(ab_dir.user_data_dir, filename)

        super().__init__(ab_dir.user_data_dir, filename)

        if "plugins_list" not in self.settings:
            self.settings.update({"plugins_list":{}})
            self.write_settings()

        self.connect_signals()

    def connect_signals(self):
        signals.delete_plugin.connect(self.remove_plugin)
        signals.plugin_imported.connect(self.add_plugin)

    @staticmethod
    def move_old_settings(directory: str, filename: str) -> None:
        """ legacy code: This function is only required for compatibility
        with the old settings file and can be removed in a future release
        """
        file = os.path.join(directory, filename)
        if not os.path.exists(file):
            package_dir = Path(__file__).resolve().parents[1]
            old_settings = os.path.join(package_dir, "ABsettings.json")
            if os.path.exists(old_settings):
                shutil.copyfile(old_settings, file)

    def get_default_settings(self) -> dict:
        """ Using methods from the commontasks file to set default settings
        """
        return {
            "custom_bw_dir": self.get_default_directory(),
            "startup_project": self.get_default_project_name(),
            "plugins_list": {}
        }

    @property
    def custom_bw_dir(self) -> str:
        """ Returns the custom brightway directory, or the default
        """
        return self.settings.get("custom_bw_dir", self.get_default_directory())

    @custom_bw_dir.setter
    def custom_bw_dir(self, directory: str) -> None:
        """ Sets the custom brightway directory to `directory`
        """
        self.settings.update({"custom_bw_dir": directory})

    @property
    def startup_project(self) -> str:
        """ Get the startup project from the settings, or the default
        """
        project = self.settings.get(
            "startup_project", self.get_default_project_name()
        )
        if project not in bw.projects:
            project = self.get_default_project_name()
        return project

    @startup_project.setter
    def startup_project(self, project: str) -> None:
        """ Sets the startup project to `project`
        """
        self.settings.update({"startup_project": project})

    @staticmethod
    def get_default_directory() -> str:
        """ Returns the default brightway application directory
        """
        return bw.projects._get_base_directories()[0]

    @staticmethod
    def get_default_project_name() -> Optional[str]:
        """ Returns the default project name.
        """
        if "default" in bw.projects:
            return "default"
        elif len(bw.projects):
            return next(iter(bw.projects)).name
        else:
            return None

    def add_plugin(self, plugin, name):
        """ Add a plugin to settings
        """
        self.settings["plugins_list"][name] = plugin.infos
        self.write_settings()
        signals.plugins_changed.emit()

    def remove_plugin(self, plugin_name: str) -> None:
        """ When a plugin is deleted from a project, the settings are also deleted.
        """
        self.settings["plugins_list"].pop(plugin_name, None)
        self.write_settings()
        signals.plugins_changed.emit()

    def get_plugins_list(self):
        """ Return a list of plugins names
        """
        list = [ n for n in self.settings["plugins_list"].keys() ]
        return list

    def get_plugins(self):
        """ Return the dictionary containing plugins infos
        """
        return self.settings["plugins_list"]


class ProjectSettings(BaseSettings):
    """
    Handles user settings which are specific to projects. Created initially to handle read-only/writable database status
    Code based on ABSettings class, if more different types of settings are needed, could inherit from a base class

    structure: singleton, loaded dependent on which project is selected.
        Persisted on disc, Stored in the BW2 projects data folder for each project
        a dictionary1 of dictionaries2
        Dictionary1 keys are settings names (currently just 'read-only-databases'), values are dictionary2s
        Dictionary2 keys are database names, values are bools

    For now, decided to not include saving writable-activities to settings.
    As activities are identified by tuples, and saving them to json requires extra code
    https://stackoverflow.com/questions/15721363/preserve-python-tuples-with-json
    This is currently not worth the effort but could be returned to later

    """
    def __init__(self, filename: str):
        # on selection of a project (signal?), find the settings file for that project if it exists
        # it can be a custom location, based on ABsettings. So check that, and if not, use default?
        # once found, load the settings or just an empty dict.
        self.connect_signals()
        super().__init__(bw.projects.dir, filename)

        # https://github.com/LCA-ActivityBrowser/activity-browser/issues/235
        # Fix empty settings file and populate with currently active databases
        if "read-only-databases" not in self.settings:
            self.settings.update(self.process_brightway_databases())
            self.write_settings()
        if "plugins_list" not in self.settings:
            self.settings.update({"plugins_list":[]})
            self.write_settings()

    def connect_signals(self):
        """ Reload the project settings whenever a project switch occurs.
        """
        signals.project_selected.connect(self.reset_for_project_selection)
        signals.plugin_selected.connect(self.add_plugin)
        signals.delete_plugin.connect(self.remove_plugin)
        signals.plugin_deselected.connect(self.remove_plugin)

    @classmethod
    def get_default_settings(cls) -> dict:
        """ Return default empty settings dictionary.
        """
        settings = cls.process_brightway_databases()
        settings["plugins_list"] = []
        return settings

    @staticmethod
    def process_brightway_databases() -> dict:
        """ Process brightway database list and return new settings dictionary.

        NOTE: This ignores the existing database read-only settings.
        """
        return {
            "read-only-databases": {name: True for name in bw.databases.list}
        }

    def reset_for_project_selection(self) -> None:
        """ On switching project, attempt to read the settings for the new
        project.
        """
        print("Reset project settings directory to:", bw.projects.dir)
        self.settings_file = os.path.join(bw.projects.dir, self.filename)
        self.initialize_settings()

    def add_db(self, db_name: str, read_only: bool = True) -> None:
        """ Store new databases and relevant settings here when created/imported
        """
        self.settings["read-only-databases"].setdefault(db_name, read_only)
        self.write_settings()

    def modify_db(self, db_name: str, read_only: bool) -> None:
        """ Update write-rules for the given database
        """
        self.settings["read-only-databases"].update({db_name: read_only})
        self.write_settings()

    def remove_db(self, db_name: str) -> None:
        """ When a database is deleted from a project, the settings are also deleted.
        """
        self.settings["read-only-databases"].pop(db_name, None)
        self.write_settings()

    def db_is_readonly(self, db_name: str) -> bool:
        """ Check if given database is read-only, defaults to yes.
        """
        return self.settings["read-only-databases"].get(db_name, True)

    def get_editable_databases(self):
        """ Return list of database names where read-only is false

        NOTE: discards the biosphere3 database based on name.
        """
        iterator = self.settings.get("read-only-databases", {}).items()
        return (name for name, ro in iterator if not ro and name != "biosphere3")

    def add_plugin(self, name: str):
        """ Add a plugin to settings
        """
        self.settings["plugins_list"].append(name)
        self.write_settings()

    def remove_plugin(self, name: str) -> None:
        """ When a plugin is deselected from a project, remove it from settings
        """
        if name in self.settings["plugins_list"]:
            self.settings["plugins_list"].remove(name)
            self.write_settings()

    def get_plugins_list(self):
        """ Return a list of plugins names
        """
        return self.settings["plugins_list"]


ab_settings = ABSettings("ABsettings.json")
project_settings = ProjectSettings("AB_project_settings.json")
