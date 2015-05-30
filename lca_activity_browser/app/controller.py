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
        if "default" in projects:
            self.select_project("default")

    def select_project(self, name):
        projects.project = name
        self.window.statusbar.center("Project: {}".format(name))
        self.window.statusbar.right("Database: None")
        self.current.database = None
        self.window.table_databases.sync()
        self.window.hide_activity_table()

    def select_database(self, item):
        if isinstance(item, str):
            name = item
        else:
            name = item.db_name
        self.current.database = Database(name)
        self.window.statusbar.right("Database: {}".format(name))
        self.window.add_activity_table(self.current.database)

    def select_activity(self, item):
        print(item.key)

    def add_database(self):
        name = self.window.dialog(
            "Create new database",
            "Name of new database:" + " " * 25
        )
        Database(name).register()
        self.window.table_databases.sync()
        self.select_database(name)
