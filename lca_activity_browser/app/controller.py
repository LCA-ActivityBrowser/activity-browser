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
        self.select_project(self.get_default_project_name())

    def get_default_project_name(self):
        if "default" in projects:
            return "default"
        else:
            return next(iter(projects)).name

    def select_project(self, name):
        projects.project = name
        signals.project_selected.emit(name)

    def new_project(self):
        name = self.window.dialog(
            "Create new project",
            "Name of new project:" + " " * 25
        )
        if name and name not in projects:
            projects.project = name
            signals.project_selected.emit(name)

    def delete_project(self):
        if len(projects) == 1:
            self.window.info("Can't delete last project")
            return
        ok = self.window.confirm((
            "Are you sure you want to delete project '{}'? It has {} databases"
            " and {} LCI methods").format(
            projects.project,
            len(databases),
            len(methods)
        ))
        if ok:
            projects.delete_project(projects.project)
            signals.project_selected.emit(self.get_default_project_name())

    def install_default_data(self):
        create_default_biosphere3()
        signals.databases_changed.emit()

    def add_database(self):
        name = self.window.dialog(
            "Create new database",
            "Name of new database:" + " " * 25
        )
        if name:
            Database(name).register()
            signals.databases_changed.emit()
            signals.database_selected.emit(name)

    def delete_database(self, *args):
        name = self.window.right_panel.inventory_tab.databases.currentItem().db_name
        ok = self.window.confirm((
            "Are you sure you want to delete database '{}'? "
            "It has {} activity datasets").format(
            name,
            len(Database(name))
        ))
        if ok:
            del databases[name]
            signals.databases_changed.emit()


    def select_calculation_setup(self, name):
        self.current.calculation_setup = name
        self.window.tables.calculation_setups.show()
        self.window.calculation_setups_list.select(name)

    def select_activity(self, item):
        self.window.graphics.lobby1.hide()
        self.window.graphics.lobby2.hide()

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

    def handle_calculation_setup_activity_table_change(self, row, col):
        if col == 1:
            self.write_current_calculation_setup()

    def handle_calculation_setup_method_table_change(self, row, col):
        self.write_current_calculation_setup()

    def write_current_calculation_setup(self):
        """Iterate over activity and methods tables, and write calculation setup to ``calculation_setups``."""
        print("Called sync_current_calculation_setup")
