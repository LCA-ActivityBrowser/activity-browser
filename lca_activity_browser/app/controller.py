# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import *
from . import Container
from .signals import signals


class Controller(object):
    def __init__(self, window):
        self.window = window
        self.current = Container()
        self.current.database = None
        if "default" in projects:
            self.select_project("default")
        else:
            self.select_project(next(iter(projects)).name)

    def select_project(self, name, force=False):
        if not name:
            return
        if name == projects.project and not force:
            return
        projects.project = name
        self.current.database = None
        signals.project_selected.emit(name)

    def select_calculation_setup(self, name):
        self.current.calculation_setup = name
        self.window.tables.calculation_setups.show()
        self.window.calculation_setups_list.select(name)

    def install_default_data(self):
        create_default_biosphere3()
        self.window.default_data_button_layout_widget.hide()
        self.window.tables.databases.sync()
        self.window.databases_table_layout_widget.show()

    # def select_database(self, item):
    #     if isinstance(item, str):
    #         name = item
    #     else:
    #         name = item.db_name
    #     self.current.database = Database(name)
    #     self.window.statusbar.right("Database: {}".format(name))
    #     self.window.add_right_inventory_tables(self.current.database)

    def select_activity(self, item):
        self.window.graphics.lobby1.hide()
        self.window.graphics.lobby2.hide()

    def add_database(self):
        name = self.window.dialog(
            "Create new database",
            "Name of new database:" + " " * 25
        )
        Database(name).register()
        self.window.tables.databases.sync()
        self.select_database(name)

    def delete_database(self, *args):
        name = self.window.tables.databases.currentItem().db_name
        print(name)
        ok = self.window.confirm((
            "Are you sure you want to delete database '{}'? "
            "It has {} activity datasets").format(
            name,
            len(Database(name))
        ))
        if ok:
            del databases[name]
            self.select_project(projects.project, force=True)

    def new_project(self):
        name = self.window.dialog(
            "Create new project",
            "Name of new project:" + " " * 25
        )
        if name:
            projects.project = name
            self.window.projects_list_widget._model.reset()
            self.select_project(name)

    def new_calculation_setup(self):
        name = self.window.dialog(
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )
        if name:
            calculation_setups[name] = {}
            signals.calculation_setup_selected.emit(name)
            self.window.calculation_setups_list._model.reset()
            self.select_calculation_setup(name)

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

    def handle_calculation_setup_activity_table_change(self, row, col):
        if col == 1:
            self.write_current_calculation_setup()

    def handle_calculation_setup_method_table_change(self, row, col):
        self.write_current_calculation_setup()

    def write_current_calculation_setup(self):
        """Iterate over activity and methods tables, and write calculation setup to ``calculation_setups``."""
        print("Called sync_current_calculation_setup")
