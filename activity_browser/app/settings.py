# -*- coding: utf-8 -*-
import json
import os
import shutil

import appdirs
import brightway2 as bw

from activity_browser.app.signals import signals
from .. import PACKAGE_DIRECTORY


class BaseSettings(object):
    """ Base Class for handling JSON settings files.
    """
    def __init__(self, directory: str, filename: str=None):
        self.data_dir = directory
        self.filename = filename or 'default_settings.json'
        self.settings_file = os.path.join(self.data_dir, self.filename)
        self.settings = None

        self.initialize_settings()

    def get_default_settings(self):
        """ Returns dictionary containing the default settings for the file

        Each child class needs to implement its own default settings.
        """
        raise NotImplementedError

    def restore_default_settings(self):
        """ Undo all user settings and return to original state.
        """
        self.settings = self.get_default_settings()
        self.write_settings()

    def initialize_settings(self):
        """ Attempt to find and read the settings_file, creates a default
        if not found
        """
        if os.path.isfile(self.settings_file):
            self.load_settings()
        else:
            self.settings = self.get_default_settings()
            self.write_settings()

    def load_settings(self):
        with open(self.settings_file, 'r') as infile:
            self.settings = json.load(infile)

    def write_settings(self):
        with open(self.settings_file, 'w') as outfile:
            json.dump(self.settings, outfile, indent=4, sort_keys=True)


class ProjectSettings():
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
    def __init__(self):
        # on selection of a project (signal?), find the settings file for that project if it exists
        # it can be a custom location, based on ABsettings. So check that, and if not, use default?
        # once found, load the settings or just an empty dict.
        self.connect_signals()

        self.project_dir = bw.projects.dir
        # print("project_dir:", self.project_dir)
        # self.project_name = bw.projects._project_name

        self.settings_file = os.path.join(self.project_dir, 'AB_project_settings.json')

        if os.path.isfile(self.settings_file):
            self.load_settings()
        else:
            # make empty dict for settings
            self.settings = self.get_default_settings()
            # save to ensure it's always accessible after first project select
            self.write_settings()

        # https://github.com/LCA-ActivityBrowser/activity-browser/issues/235
        # Fix empty settings file and populate with currently active databases
        if 'read-only-databases' not in self.settings:
            self.settings.update(self.process_brightway_databases())
            self.write_settings()

    def connect_signals(self):
        signals.project_selected.connect(self.reset_for_project_selection)
        signals.delete_project.connect(self.reset_for_project_selection)

    def get_default_settings(self):
        """ Return default empty settings dictionary.
        """
        default = {
            'read-only-databases': {}
        }
        return default

    def process_brightway_databases(self):
        """ Process brightway database list and return new settings dictionary.

        NOTE: This ignores the existing database read-only settings.
        """
        settings = {
            'read-only-databases': {
                name: True for name in bw.databases.list
            }
        }
        return settings

    def load_settings(self):
        with open(self.settings_file, 'r') as infile:
            self.settings = json.load(infile)

    def write_settings(self):
        with open(self.settings_file, 'w') as outfile:
            json.dump(self.settings, outfile, indent=4, sort_keys=True)
            # print("user settings written to", str(self.settings_file), "\n\t", str(self.settings))

    def reset_for_project_selection(self):
        # todo: better implementation? reinitialise settings object each time instead
        # executes when new project selected
        # same code as __init__ but without connect_signals()
        self.project_dir = bw.projects.dir
        print('Reset project settings directory to:', self.project_dir)
        self.settings_file = os.path.join(self.project_dir, 'AB_project_settings.json')

        # load if found, else make empty dict and save as new file
        if os.path.isfile(self.settings_file):
            self.load_settings()
        else:
            self.settings = self.get_default_settings()
            self.write_settings()

    def add_db(self, db_name, read_only=True):
        """ Store new databases and relevant settings here when created/imported
        """
        self.settings['read-only-databases'].setdefault(db_name, read_only)
        self.write_settings()

    def modify_db(self, db_name, read_only):
        """ Update write-rules for the given database
        """
        self.settings['read-only-databases'].update({db_name: read_only})
        self.write_settings()

    def remove_db(self, db_name):
        """ When a database is deleted from a project, the settings are also deleted.
        """
        self.settings['read-only-databases'].pop(db_name, None)
        self.write_settings()


ab_settings = ABSettings()
project_settings = ProjectSettings()

