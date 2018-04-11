# -*- coding: utf-8 -*-
import os
import copy
import uuid

import brightway2 as bw
from bw2data.backends.peewee import Exchange
from bw2data.project import ProjectDataset, SubstitutableDatabase
from PyQt5 import QtWidgets

from .signals import signals
from .ui.db_import_wizard import (
    DatabaseImportWizard, DefaultBiosphereDialog, CopyDatabaseDialog
)
from .settings import ab_settings
from .bwutils import commontasks as bc


class Controller(object):
    def __init__(self, window):
        self.window = window
        self.connect_signals()
        signals.project_selected.emit()
        self.load_settings()
        self.db_wizard = None
        print('Brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        print('Brightway2 active project: {}'.format(bw.projects.current))

    def load_settings(self):
        if ab_settings.settings:
            print("Loading user settings:")
            if ab_settings.settings.get('custom_bw_dir'):
                self.switch_brightway2_dir_path(dirpath=ab_settings.settings['custom_bw_dir'])
            if ab_settings.settings.get('startup_project'):
                self.change_project(ab_settings.settings['startup_project'])

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
        signals.copy_to_db.connect(self.copy_to_db)
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
        signals.switch_bw2_dir_path.connect(self.switch_brightway2_dir_path)

    def import_database_wizard(self):
        if self.db_wizard is None:
            self.db_wizard = DatabaseImportWizard()
        else:
            self.db_wizard.show()
            self.db_wizard.activateWindow()

    def switch_brightway2_dir_path(self, dirpath):
        if dirpath == bw.projects._base_data_dir:
            return  # dirpath is already loaded
        try:
            assert os.path.isdir(dirpath)
            bw.projects._base_data_dir = dirpath
            bw.projects._base_logs_dir = os.path.join(dirpath, "logs")
            # create folder if it does not yet exist
            if not os.path.isdir(bw.projects._base_logs_dir):
                os.mkdir(bw.projects._base_logs_dir)
            # load new brightway directory
            bw.projects.db = SubstitutableDatabase(
                os.path.join(bw.projects._base_data_dir, "projects.db"),
                [ProjectDataset]
            )
            print('Loaded brightway2 data directory: {}'.format(bw.projects._base_data_dir))
            self.change_project(bc.get_startup_project_name(), reload=True)
            signals.databases_changed.emit()

        except AssertionError:
            print('Could not access BW_DIR as specified in settings.py')

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
        elif name not in [p.name for p in bw.projects]:
            print("Project does not exist: {}".format(name))
            return

        if name != bw.projects.current or reload:
            bw.projects.set_current(name)
            signals.project_selected.emit()
            print("Loaded project:", name)

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
            self.change_project(bc.get_startup_project_name(), reload=True)
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
        name = self.window.left_panel.LCA_setup_tab.list_widget.name
        del bw.calculation_setups[name]
        self.window.left_panel.LCA_setup_tab.set_default_calculation_setup()
        print("Deleted calculation setup: {}".format(name))

    def rename_calculation_setup(self):
        current = self.window.left_panel.LCA_setup_tab.list_widget.name
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
        current = self.window.left_panel.LCA_setup_tab.list_widget.name
        if current:
            bw.calculation_setups[current] = {
                'inv': self.window.left_panel.LCA_setup_tab.activities_table.to_python(),
                'ia': self.window.left_panel.LCA_setup_tab.methods_table.to_python()
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

    def generate_copy_code(self, key):
        if '_copy' in key[1]:
            code = key[1].split('_copy')[0]
        else:
            code = key[1]
        copies = [a['code'] for a in bw.Database(key[0]) if
                  code in a['code'] and '_copy' in a['code']]
        if copies:
            n = max([int(c.split('_copy')[1]) for c in copies])
            new_code = code + '_copy' + str(n + 1)
        else:
            new_code = code + '_copy1'
        return new_code

    def copy_activity(self, key):
        act = bw.get_activity(key)
        new_code = self.generate_copy_code(key)
        new_act = act.copy(new_code)
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

    def copy_to_db(self, activity_key):
        origin_db = activity_key[0]
        activity = bw.get_activity(activity_key)
        # TODO: Exclude read-only dbs from target_dbs as soon as they are implemented
        available_target_dbs = sorted(set(bw.databases).difference(
            {'biosphere3', origin_db}
        ))
        if not available_target_dbs:
            self.window.warning(
                "No target database",
                "No valid target databases available. Create a new database first."
            )
        else:
            target_db, ok = QtWidgets.QInputDialog.getItem(
                self.window,
                "Copy activity to database",
                "Target database:",
                available_target_dbs,
                0,
                False
            )
            if ok:
                new_code = self.generate_copy_code((target_db, activity['code']))
                activity.copy(code=new_code, database=target_db)
                # only process database immediatly if small
                if len(bw.Database(target_db)) < 200:
                    bw.databases.clean()
                signals.database_changed.emit(target_db)
                signals.databases_changed.emit()

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
