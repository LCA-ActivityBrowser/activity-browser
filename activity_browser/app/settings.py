# -*- coding: utf-8 -*-
import os
import json
import shutil

import appdirs
from activity_browser.app.bwutils import commontasks as bc
from .. import PACKAGE_DIRECTORY
import brightway2 as bw
from activity_browser.app.signals import signals

class ABSettings():
    def __init__(self):
        ab_dir = appdirs.AppDirs('ActivityBrowser', 'ActivityBrowser')
        self.data_dir = ab_dir.user_data_dir
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        self.settings_file = os.path.join(self.data_dir, 'ABsettings.json')
        self.move_old_settings()
        if os.path.isfile(self.settings_file):
            self.load_settings()
        else:
            self.settings = {}

    def move_old_settings(self):
        if not os.path.exists(self.settings_file):
            old_settings = os.path.join(PACKAGE_DIRECTORY, 'ABsettings.json')
            if os.path.exists(old_settings):
                shutil.copyfile(old_settings, self.settings_file)

    def load_settings(self):
        with open(self.settings_file, 'r') as infile:
            self.settings = json.load(infile)

    def write_settings(self):
        with open(self.settings_file, 'w') as outfile:
            json.dump(self.settings, outfile, indent=4, sort_keys=True)


class UserProjectSettings():
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
            self.settings = {}
            # save to ensure it's always accessible after first project select
            self.write_settings()

    def load_settings(self):
        with open(self.settings_file, 'r') as infile:
            self.settings = json.load(infile)

    def write_settings(self):
        with open(self.settings_file, 'w') as outfile:
            json.dump(self.settings, outfile, indent=4, sort_keys=True)
            # print("user settings written to", str(self.settings_file), "\n\t", str(self.settings))

    def reset_for_project_selection(self):
        # executes when new project selected
        # same code as __init__ but without connect_signals()
        self.project_dir = bw.projects.dir
        # print("project_dir:", self.project_dir)
        # self.project_name = bw.projects._project_name

        self.settings_file = os.path.join(self.project_dir, 'AB_project_settings.json')

        # load if found, else make empty dict and save as new file
        if os.path.isfile(self.settings_file):
            self.load_settings()
        else:
            self.settings = self.get_default_settings()
            self.write_settings()

    def get_default_settings(self):
        # returns default empty settings dictionary
        default = {
            'read-only-databases': {}
            # ,'writable-activities': {}
        }
        return default

    def connect_signals(self):
        signals.project_selected.connect(self.reset_for_project_selection)


ab_settings = ABSettings()
user_project_settings = UserProjectSettings()
