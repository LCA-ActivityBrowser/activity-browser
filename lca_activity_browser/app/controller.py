# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import *
from . import Container



class Controller(object):
    def __init__(self, window):
        self.window = window
        self.current = Container()
        self.current.database = None

    def select_project(self, item):
        name = item.data()
        projects.project = name
        self.window.statusbar.center("Project: {}".format(name))
        self.window.statusbar.right("Database: None")
        self.current.database = None
        self.window.table_databases.reset()
        self.window.select_tab(
            self.window.databases_tab_container,
            "right"
        )

    def select_database(self, item):
        name = item.data()
        self.current.database = Database(name)
        self.window.statusbar.right("Database: {}".format(name))
