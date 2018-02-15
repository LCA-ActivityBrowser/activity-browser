# -*- coding: utf-8 -*-
import os
import json

import appdirs


class ABSettings():
    def __init__(self):
        ab_dir = appdirs.AppDirs('ActivityBrowser', 'ActivityBrowser')
        self.settings_dir = ab_dir.user_data_dir
        if not os.path.isdir(self.settings_dir):
            os.mkdir(self.settings_dir)
        self.settings_file = os.path.join(self.settings_dir, 'ABsettings.json')
        if os.path.isfile(self.settings_file):
            self.load_settings()
        else:
            self.settings = {}

    def load_settings(self):
        with open(self.settings_file, 'r') as infile:
            self.settings = json.load(infile)

    def write_settings(self):
        with open(self.settings_file, 'w') as outfile:
            json.dump(self.settings, outfile, indent=4, sort_keys=True)


ab_settings = ABSettings()
