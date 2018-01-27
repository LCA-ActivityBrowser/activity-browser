# -*- coding: utf-8 -*-
import os
import copy
import uuid

import brightway2 as bw
from bw2data.backends.peewee import Exchange
from bw2data.project import ProjectDataset, create_database
from PyQt5 import QtWidgets

from .signals import signals
from .ui.db_import_wizard import (
    DatabaseImportWizard, DefaultBiosphereDialog, CopyDatabaseDialog
)
try:
    from . import settings
except ImportError:
    settings = None


class Controller(object):
    def __init__(self, window):
        self.window = window
        self.connect_signals()
        print('Brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        print('Brightway2 active project: {}'.format(bw.projects.current))

        # switch directly to custom bw2 directory and project, if specified in settings
        # else use default bw2 path and project
        current_project = self.get_default_project_name()
        signals.project_selected.emit()
        if settings:
            if hasattr(settings, "BW2_DIR"):
                print("Loading brightway2 data directory from settings...")
                self.switch_brightway2_dir_path(dirpath=settings.BW2_DIR)
            if hasattr(settings, "PROJECT_NAME"):
                print("Loading project from settings...")
                self.change_project(settings.PROJECT_NAME)

        self.db_wizard = None

    def connect_signals(self):
        # SLOTS
        # Project
        signals.new_project.connect(self.new_project)
        signals.change_project.connect(self.change_project)
        signals.change_project_dialogue.connect(self.change_project_dialogue)
        signals.copy_project.connect(self.copy_project)
        signals.delete_project.connect(self.delete_project)
        # Database
        signals.add_database.connect(self.add_database)
        signals.delete_database.connect(self.delete_database)
        signals.copy_database.connect(self.copy_database)
        signals.install_default_data.connect(self.install_default_data)
        signals.import_database.connect(self.import_database_wizard)
        # Activity
        signals.copy_activity.connect(self.copy_activity)
        signals.activity_modified.connect(self.modify_activity)
        signals.new_activity.connect(self.new_activity)
        signals.delete_activity.connect(self.delete_activity)
        # Exchange
        signals.exchanges_output_modified.connect(self.modify_exchanges_output)
        signals.exchanges_deleted.connect(self.delete_exchanges)
        signals.exchanges_add.connect(self.add_exchanges)
        signals.exchange_amount_modified.connect(self.modify_exchange_amount)
        # Calculation Setups
        signals.new_calculation_setup.connect(self.new_calculation_setup)
        signals.calculation_setup_changed.connect(self.write_current_calculation_setup)
        signals.rename_calculation_setup.connect(self.rename_calculation_setup)
        signals.delete_calculation_setup.connect(self.delete_calculation_setup)
        # Other
        signals.switch_bw2_dir_path.connect(self.select_bw2_dir_path)

    def import_database_wizard(self):
        if self.db_wizard is None:
            self.db_wizard = DatabaseImportWizard()
        else:
            self.db_wizard.show()
            self.db_wizard.activateWindow()

    def select_bw2_dir_path(self):
        folder_path = QtWidgets.QFileDialog().getExistingDirectory(
            None, "Select a brightway2 database folder")
        # TODO: in case of a directory that does not contain an existing brightway2 database,
        # ask if a new db should be set up
        print(folder_path)
        self.switch_brightway2_dir_path(folder_path)
        return folder_path

    def switch_brightway2_dir_path(self, dirpath):
        try:
            assert os.path.isdir(dirpath)
            bw.projects._base_data_dir = dirpath
            bw.projects._base_logs_dir = os.path.join(dirpath, "logs")
            # create folder if it does not yet exist
            if not os.path.isdir(bw.projects._base_logs_dir):
                os.mkdir(bw.projects._base_logs_dir)
            bw.projects.db.close()
            bw.projects.db = create_database(
                os.path.join(bw.projects._base_data_dir, "projects.db"),
                [ProjectDataset]
            )
            self.change_project(self.get_default_project_name())
            print('Changed brightway2 data directory to: {}'.format(bw.projects._base_data_dir))

        except AssertionError:
            print('Could not access BW_DIR as specified in settings.py')

    def get_default_project_name(self):
        if "default" in bw.projects:
            return "default"
        else:
            return next(iter(bw.projects)).name

    def change_project_dialogue(self):
        project_names = sorted([x.name for x in bw.projects])
        name, ok = QtWidgets.QInputDialog.getItem(
            self.window,
            "Choose project",
            "Name:",
            project_names,
            project_names.index(bw.projects.current),
            False
        )
        if ok:
            self.change_project(name)

    def change_project(self, name=None, reload=False):
        # TODO: what should happen if a new project is opened? (all activities, etc. closed?)
        if not name:
            print("No project name given.")
            return
        if name not in [p.name for p in bw.projects]:
            print("Project does not exist: {}".format(name))
            return
        if name != bw.projects.current or reload:
            bw.projects.set_current(name)
            signals.project_selected.emit()
            print("Changed project to:", name)

    def get_new_project_name(self, parent):
        name, status = QtWidgets.QInputDialog.getText(
            parent,
            "Create new project",
            "Name of new project:" + " " * 25
        )
        return name

    def new_project(self):
        name = self.get_new_project_name(self.window)
        if name and name not in bw.projects:
            bw.projects.set_current(name)
            self.change_project(name, reload=True)
            signals.projects_changed.emit()
        elif name in bw.projects:
            self.window.info("A project with this name already exists.")

    def copy_project(self):
        name = self.window.dialog(
            "Copy current project",
            "Copy current project ({}) to new name:".format(bw.projects.current) + " " * 10
        )
        if name and name not in bw.projects:
            bw.projects.copy_project(name, switch=True)
            self.change_project(name)
            signals.projects_changed.emit()
        else:
            self.window.info("A project with this name already exists.")

    def confirm_project_deletion(self, parent):
        confirm = QtWidgets.QMessageBox.question(
            parent,
            'Confirm project deletion',
            ("Are you sure you want to delete project '{}'? It has {} databases" +
             " and {} LCI methods").format(
                bw.projects.current,
                len(bw.databases),
                len(bw.methods)
            )
        )
        return confirm

    def delete_project(self):
        if len(bw.projects) == 1:
            self.window.info("Can't delete last project")
            return
        ok = self.confirm_project_deletion(self.window)
        if ok:
            bw.projects.delete_project(bw.projects.current)
            self.change_project(self.get_default_project_name(), reload=True)
            signals.projects_changed.emit()

    def install_default_data(self):
        self.default_biosphere_dialog = DefaultBiosphereDialog()

    def add_database(self):
        name = self.window.dialog(
            "Create new database",
            "Name of new database:" + " " * 25
        )
        if name:
            if name not in bw.databases:
                bw.Database(name).register()
                signals.databases_changed.emit()
                signals.database_selected.emit(name)
            else:
                self.window.info("A database with this name already exists.")

    def copy_database(self, name):
        new_name = self.window.dialog(
            "Copy {}".format(name),
            "Name of new database:" + " " * 25)
        if new_name:
            if new_name not in bw.databases:
                self.copydb_dialog = CopyDatabaseDialog(name, new_name)
            else:
                self.window.info('Database <b>{}</b> already exists!'.format(new_name))

    def delete_database(self, name):
        ok = self.window.confirm((
            "Are you sure you want to delete database '{}'? "
            "It has {} activity datasets").format(
            name,
            len(bw.Database(name))
        ))
        if ok:
            del bw.databases[name]
            self.change_project(bw.projects.current, reload=True)

    def new_calculation_setup(self):
        name = self.window.dialog(
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )
        if name:
            # TODO: prevent that existing calculation setups get overwritten
            bw.calculation_setups[name] = {'inv': [], 'ia': []}
            signals.calculation_setup_selected.emit(name)
            print("New calculation setup: {}".format(name))

    def delete_calculation_setup(self):
        name = self.window.left_panel.cs_tab.list_widget.name
        del bw.calculation_setups[name]
        self.window.left_panel.cs_tab.set_default_calculation_setup()
        print("Deleted calculation setup: {}".format(name))

    def rename_calculation_setup(self):
        current = self.window.left_panel.cs_tab.list_widget.name
        new_name = self.window.dialog(
            "Rename '{}'".format(current),
            "New name of this calculation setup:" + " " * 10
        )
        if new_name:
            bw.calculation_setups[new_name] = bw.calculation_setups[current].copy()
            print("Current setups:", list(bw.calculation_setups.keys()))
            del bw.calculation_setups[current]
            print("After deletion of {}:".format(current), list(bw.calculation_setups.keys()))
            signals.calculation_setup_selected.emit(new_name)

    def write_current_calculation_setup(self):
        """Iterate over activity and methods tables, and write
        calculation setup to ``calculation_setups``."""
        current = self.window.left_panel.cs_tab.list_widget.name
        if current:
            bw.calculation_setups[current] = {
                'inv': self.window.left_panel.cs_tab.activities_table.to_python(),
                'ia': self.window.left_panel.cs_tab.methods_table.to_python()
            }

    def new_activity(self, database_name):
        # TODO: let user define product
        name = self.window.dialog(
            "Create new technosphere activity",
            "Name of new technosphere activity:" + " " * 10
        )
        if name:
            new_act = bw.Database(database_name).new_activity(
                code=uuid.uuid4().hex,
                name=name,
                unit="unit",
                type="process",
            )
            new_act.save()
            production_exchange = new_act.new_exchange(amount=1, type="production")
            production_exchange.input = new_act
            production_exchange.save()
            signals.open_activity_tab.emit("right", new_act.key)
            signals.database_changed.emit(database_name)

    def delete_activity(self, key):
        act = bw.get_activity(key)
        bw.database = act['database']
        nu = len(act.upstream())
        if nu:
            text = "activities consume" if nu > 1 else "activity consumes"
            self.window.warning(
                "Can't delete activity",
                """Can't delete {}.
{} upstream {} its reference product.
Upstream exchanges must be modified or deleted.""".format(act, nu, text)
            )
        else:
            act.delete()
            signals.database_changed.emit(act['database'])

    def copy_activity(self, key):
        act = bw.get_activity(key)
        new_act = act.copy("Copy of " + act['name'])
        # Update production exchanges
        for exc in new_act.production():
            if exc.input.key == key:
                exc.input = new_act
                exc.save()
        # Update 'products'
        for product in new_act.get('products', []):
            if product.get('input') == key:
                product['input'] = new_act.key
        new_act.save()
        signals.database_changed.emit(act['database'])
        signals.open_activity_tab.emit("right", new_act.key)

    def modify_activity(self, key, field, value):
        activity = bw.get_activity(key)
        activity[field] = value
        activity.save()
        signals.database_changed.emit(key[0])

    def modify_exchanges_output(self, exchanges, key):
        db_changed = {key[0]}
        for exc in exchanges:
            db_changed.add(exc['output'][0])
            if exc['type'] == 'production':
                new_exc = Exchange()
                new_exc._data = copy.deepcopy(exc._data)
                new_exc['type'] = 'technosphere'
                new_exc['output'] = key
                new_exc.save()
            else:
                exc['output'] = key
                exc.save()
        for db in db_changed:
            signals.database_changed.emit(db)

    def add_exchanges(self, from_keys, to_key):
        activity = bw.get_activity(to_key)
        for key in from_keys:
            from_act = bw.get_activity(key)
            exc = activity.new_exchange(input=key, amount=1)
            if key == to_key:
                exc['type'] = 'production'
            elif from_act.get('type', 'process') == 'process':
                exc['type'] = 'technosphere'
            elif from_act.get('type') == 'emission':
                exc['type'] = 'biosphere'
            else:
                exc['type'] = 'unknown'
            exc.save()
        signals.database_changed.emit(to_key[0])

    def delete_exchanges(self, exchanges):
        db_changed = set()
        for exc in exchanges:
            db_changed.add(exc['output'][0])
            exc._document.delete_instance()
        for db in db_changed:
            signals.database_changed.emit(db)

    def modify_exchange_amount(self, exchange, value):
        exchange['amount'] = value
        exchange.save()
        signals.database_changed.emit(exchange['output'][0])
