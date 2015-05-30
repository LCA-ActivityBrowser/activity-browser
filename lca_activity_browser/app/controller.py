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
        else:
            self.select_project(next(iter(projects)).name)

    def select_project(self, name):
        if not name or name == projects.project:
            return
        projects.project = name
        self.window.statusbar.center("Project: {}".format(name))
        self.window.statusbar.right("Database: None")
        self.current.database = None
        self.window.table_databases.sync()
        self.window.hide_activity_table()
        self.window.hide_cfs_table()
        index = sorted([project.name for project in projects]).index(projects.project)
        self.window.projects_list_widget.setCurrentIndex(index)

        if not len(databases):
            self.window.default_data_button_layout_widget.show()
            self.window.databases_table_layout_widget.hide()
        else:
            self.window.default_data_button_layout_widget.hide()
            self.window.databases_table_layout_widget.show()

    def install_default_data(self):
        create_default_biosphere3()
        self.window.default_data_button_layout_widget.hide()
        self.window.table_databases.sync()
        self.window.databases_table_layout_widget.show()

    def select_database(self, item):
        if isinstance(item, str):
            name = item
        else:
            name = item.db_name
        self.current.database = Database(name)
        self.window.statusbar.right("Database: {}".format(name))
        self.window.add_activity_table(self.current.database)

    def select_activity(self, item):
        pass

    def add_database(self):
        name = self.window.dialog(
            "Create new database",
            "Name of new database:" + " " * 25
        )
        Database(name).register()
        self.window.table_databases.sync()
        self.select_database(name)

    def new_project(self):
        name = self.window.dialog(
            "Create new project",
            "Name of new project:" + " " * 25
        )
        if name:
            projects.project = name
            self.window.projects_list_widget._model.reset()
            self.select_project(name)

    def delete_project(self):
        ok = self.window.confirm((
            "Are you sure you want to delete project '{}'? It has {} databases"
            " and {} LCI methods").format(
            projects.project,
            len(databases),
            len(methods)
        ))
        if ok:
            projects.delete_project(projects.project)
            self.window.projects_list_widget._model.reset()
            self.select_project(projects.project)

    def select_method(self, item):
        method = item.method
        self.current.method = method
        self.window.add_cfs_table(method)
        self.window.select_tab(self.window.cfs_tab_container, "left")
