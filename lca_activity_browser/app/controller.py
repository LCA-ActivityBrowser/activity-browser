# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import *
from . import Container
from .signals import signals
from .ui.widgets import ActivityDataGrid
import sys


class Controller(object):
    def __init__(self, window):
        self.window = window
        self.current = Container()
        self.select_project(self.get_default_project_name())

        signals.calculation_setup_changed.connect(
            self.write_current_calculation_setup
        )
        signals.copy_activity.connect(self.copy_activity)

    def get_default_project_name(self):
        if "default" in projects:
            return "default"
        else:
            return next(iter(projects)).name

    def select_project(self, name):
        projects.current = name
        signals.project_selected.emit(name)

    def new_project(self):
        name = self.window.dialog(
            "Create new project",
            "Name of new project:" + " " * 25
        )
        if name and name not in projects:
            projects.current = name
            signals.project_selected.emit(name)

    def copy_project(self):
        name = self.window.dialog(
            "Copy current project",
            "Copy current project ({}) to new name:".format(projects.current) + " " * 10
        )
        if name and name not in projects:
            projects.copy_project(name, switch=True)
            signals.project_selected.emit(name)

    def delete_project(self):
        if len(projects) == 1:
            self.window.info("Can't delete last project")
            return
        ok = self.window.confirm((
            "Are you sure you want to delete project '{}'? It has {} databases"
            " and {} LCI methods").format(
            projects.current,
            len(databases),
            len(methods)
        ))
        if ok:
            projects.delete_project(projects.current)
            signals.project_selected.emit(self.get_default_project_name())

    def install_default_data(self):
        create_default_biosphere3()
        if not len(methods):
            create_default_lcia_methods()
        if not len(migrations):
            create_core_migrations()
        signals.project_selected.emit(projects.current)

    def add_database(self):
        name = self.window.dialog(
            "Create new database",
            "Name of new database:" + " " * 25
        )
        if name:
            Database(name).register()
            signals.databases_changed.emit()
            signals.database_selected.emit(name)

    def copy_database(self, name):
        name = self.window.right_panel.inventory_tab.databases.currentItem().db_name
        new_name = self.window.dialog(
            "Copy {}".format(name),
            "Name of new database:" + " " * 25)
        if new_name:
            Database(name).copy(new_name)
            signals.databases_changed.emit()

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
            signals.project_selected.emit(projects.current)

    def new_calculation_setup(self):
        name = self.window.dialog(
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )
        if name:
            calculation_setups[name] = {'inv': [], 'ia': []}
            signals.calculation_setup_selected.emit(name)

    def delete_calculation_setup(self):
        name = self.window.left_panel.cs_tab.list_widget.name
        del calculation_setups[name]
        self.window.left_panel.cs_tab.set_default_calculation_setup()

    def rename_calculation_setup(self):
        current = self.window.left_panel.cs_tab.list_widget.name
        new_name = self.window.dialog(
            "Rename '{}'".format(current),
            "New name of this calculation setup:" + " " * 10
        )
        if new_name:
            calculation_setups[new_name] = calculation_setups[current]
            del calculation_setups[current]
            signals.calculation_setup_selected.emit(new_name)

    def write_current_calculation_setup(self):
        """Iterate over activity and methods tables, and write calculation setup to ``calculation_setups``."""
        current = self.window.left_panel.cs_tab.list_widget.name
        calculation_setups[current] = {
            'inv': self.window.left_panel.cs_tab.activities_table.to_python(),
            'ia': self.window.left_panel.cs_tab.methods_table.to_python()
        }

    def copy_activity(self, key):
        act = get_activity(key)
        self.window.right_panel.addTab(ActivityDataGrid(activity=act), 'Foo')
