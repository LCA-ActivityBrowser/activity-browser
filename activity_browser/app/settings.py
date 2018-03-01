# -*- coding: utf-8 -*-
import os
import json

from .. import PACKAGE_DIRECTORY


class ABSettings():
    def __init__(self):
        self.settings_file = os.path.join(PACKAGE_DIRECTORY, 'ABsettings.json')
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
