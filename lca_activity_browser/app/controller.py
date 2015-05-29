# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from bw2data import projects


class Controller(object):
    def __init__(self, window):
        self.window = window

    def select_project(self, item):
        name = item.data()
        projects.project = name
        self.window.statusbar.center("Project: {}".format(name))
