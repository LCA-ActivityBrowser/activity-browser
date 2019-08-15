# -*- coding: utf-8 -*-
import os
import uuid

import brightway2 as bw
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSlot
from bw2data.backends.peewee import sqlite3_lci_db
from bw2data.project import ProjectDataset, SubstitutableDatabase

from activity_browser.app.ui.wizards.db_import_wizard import (
    DatabaseImportWizard, DefaultBiosphereDialog, CopyDatabaseDialog
)
from .bwutils import commontasks as bc
from .settings import ab_settings, project_settings
from .signals import signals


class Controller(object):
    """The Controller is a central object in the Activity Browser. It groups methods that may be required in different
    parts of the AB to access, modify, or delete:
    - settings
    - projects
    - databases
    - calculation setups
    - activities/exchanges
    It is different from bwutils in that it also contains Qt elements such as dialogs.
    - """
    def __init__(self):
        self.connect_signals()
        signals.project_selected.emit()
        self.load_settings()
        self.db_wizard = None
        print('Brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        print('Brightway2 active project: {}'.format(bw.projects.current))

    def connect_signals(self):
        # SLOTS
        # Project
        signals.project_selected.connect(self.ensure_sqlite_indices)
        signals.new_project.connect(self.new_project)
        signals.change_project.connect(self.change_project)
        # signals.change_project_dialog.connect(self.change_project_dialog)
        signals.copy_project.connect(self.copy_project)
        signals.delete_project.connect(self.delete_project)
        # Database
        signals.add_database.connect(self.add_database)
        signals.delete_database.connect(self.delete_database)
        signals.copy_database.connect(self.copy_database)
        signals.install_default_data.connect(self.install_default_data)
        signals.import_database.connect(self.import_database_wizard)
        # Activity
        signals.duplicate_activity.connect(self.duplicate_activity)
        signals.activity_modified.connect(self.modify_activity)
        signals.new_activity.connect(self.new_activity)
        signals.delete_activity.connect(self.delete_activity)
        signals.duplicate_activity_to_db.connect(self.duplicate_activity_to_db)
        signals.show_duplicate_to_db_interface.connect(self.show_duplicate_to_db_interface)
        # Exchange
        # signals.exchanges_output_modified.connect(self.modify_exchanges_output)
        signals.exchanges_deleted.connect(self.delete_exchanges)
        signals.exchanges_add.connect(self.add_exchanges)
        signals.exchange_modified.connect(self.modify_exchange)
        # Calculation Setups
        signals.new_calculation_setup.connect(self.new_calculation_setup)
        signals.rename_calculation_setup.connect(self.rename_calculation_setup)
        signals.delete_calculation_setup.connect(self.delete_calculation_setup)
        # Other
        signals.switch_bw2_dir_path.connect(self.switch_brightway2_dir_path)

# SETTINGS
    def load_settings(self):
        if ab_settings.settings:
            print("Loading user settings:")
            if ab_settings.settings.get('custom_bw_dir'):
                self.switch_brightway2_dir_path(dirpath=ab_settings.settings['custom_bw_dir'])
            if ab_settings.settings.get('startup_project'):
                self.change_project(ab_settings.settings['startup_project'])

    def import_database_wizard(self):
        try:
            if self.db_wizard is None:
                self.db_wizard = DatabaseImportWizard()
            else:
                self.db_wizard.show()
                self.db_wizard.activateWindow()
        except:
            QtWidgets.QMessageBox.warning(None,
                                              "Error during importing.",
                                              "Oops. Something went wrong with the data import. "
                                              "Please check the console for details.")

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

# PROJECT
    def change_project_dialog(self):
        project_names = sorted([x.name for x in bw.projects])
        name, ok = QtWidgets.QInputDialog.getItem(
            None,
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

    def get_new_project_name_dialog(self):
        name, ok = QtWidgets.QInputDialog.getText(
            None,
            "Create new project",
            "Name of new project:" + " " * 25
        )
        return name if ok else None

    def new_project(self, name=None):
        name = name or self.get_new_project_name_dialog()
        if name and name not in bw.projects:
            bw.projects.set_current(name)
            self.change_project(name, reload=True)
            signals.projects_changed.emit()
        elif name in bw.projects:
            QtWidgets.QMessageBox.information(None,
                                              "Not possible.",
                                              "A project with this name already exists.")

    def copy_project(self):
        name, ok = QtWidgets.QInputDialog.getText(
            None,
            "Copy current project",
            "Copy current project ({}) to new name:".format(bw.projects.current) + " " * 10
        )
        if ok and name:
            if name not in bw.projects:
                bw.projects.copy_project(name, switch=True)
                self.change_project(name)
                signals.projects_changed.emit()
            else:
                QtWidgets.QMessageBox.information(None,
                                                  "Not possible.",
                                                  "A project with this name already exists.")

    def confirm_project_deletion_dialog(self):
        buttonReply = QtWidgets.QMessageBox.question(
            None,
            'Confirm project deletion',
            ("Are you sure you want to delete project '{}'? It has {} databases" +
             " and {} LCI methods").format(
                bw.projects.current,
                len(bw.databases),
                len(bw.methods)
            )
        )
        return buttonReply

    def delete_project(self):
        if len(bw.projects) == 1:
            QtWidgets.QMessageBox.information(None,
                                              "Not possible",
                                              "Can't delete last project.")
            return
        buttonReply = self.confirm_project_deletion_dialog()
        # truely deleting does not work due to a permission error on Windows
        # delete_dir = QtWidgets.QMessageBox.question(None,
        #     'Confirm project deletion',
        #     "Do you also want to delete the files on your hard drive?")
        if buttonReply == QtWidgets.QMessageBox.Yes:
            bw.projects.delete_project(bw.projects.current, delete_dir=False)
            self.change_project(bc.get_startup_project_name(), reload=True)
            # if delete_dir:  # also purging does not work (PermissionError)
            #     bw.projects.purge_deleted_directories()
            signals.projects_changed.emit()

# DATABASE
    def ensure_sqlite_indices(self):
        """
        - fix for https://github.com/LCA-ActivityBrowser/activity-browser/issues/189
        - also see bw2data issue: https://bitbucket.org/cmutel/brightway2-data/issues/60/massive-sqlite-query-performance-decrease
        @LegacyCode?
        """
        if bw.databases and not sqlite3_lci_db._database.get_indexes('activitydataset'):
            print('creating missing sqlite indices')
            bw.Database(list(bw.databases)[-1])._add_indices()

    def install_default_data(self):
        self.default_biosphere_dialog = DefaultBiosphereDialog()
        project_settings.add_db("biosphere3")

    def add_database(self):
        name, ok = QtWidgets.QInputDialog.getText(
            None,
            "Create new database",
            "Name of new database:" + " " * 25
        )

        if ok and name:
            if name not in bw.databases:
                bw.Database(name).register()
                project_settings.add_db(name)
                signals.databases_changed.emit()
                signals.database_selected.emit(name)
            else:
                QtWidgets.QMessageBox.information(None,
                                                  "Not possible",
                                                  "A database with this name already exists.")

    def copy_database(self, name):
        new_name, ok = QtWidgets.QInputDialog.getText(
            None,
            "Copy {}".format(name),
            "Name of new database:" + " " * 25)
        if ok and new_name:
            if new_name not in bw.databases:
                self.copydb_dialog = CopyDatabaseDialog(name, new_name)
                project_settings.add_db(new_name)
            else:
                QtWidgets.QMessageBox.information(None,
                                                  "Not possible",
                                                  'Database <b>{}</b> already exists!'.format(new_name))

    def delete_database(self, name):
        ok = QtWidgets.QMessageBox.question(
            None,
            "Delete database?",
            ("Are you sure you want to delete database '{}'? It has {} activity datasets").format(
                name, len(bw.Database(name)))
        )
        if ok:
            project_settings.remove_db(name)
            del bw.databases[name]
            self.change_project(bw.projects.current, reload=True)

# CALCULATION SETUP
    def new_calculation_setup(self):
        name, ok = QtWidgets.QInputDialog.getText(
            None,
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )
        if ok and name:
            if name not in bw.calculation_setups.keys():
                bw.calculation_setups[name] = {'inv': [], 'ia': []}
                signals.calculation_setup_selected.emit(name)
                print("New calculation setup: {}".format(name))
            else:
                QtWidgets.QMessageBox.information(None,
                                                  "Not possible",
                                                  "A calculation setup with this name already exists.")

    def delete_calculation_setup(self, name):
        del bw.calculation_setups[name]
        signals.set_default_calculation_setup.emit()
        print("Deleted calculation setup: {}".format(name))

    def rename_calculation_setup(self, current):
        new_name, ok = QtWidgets.QInputDialog.getText(
            None,
            "Rename '{}'".format(current),
            "New name of this calculation setup:" + " " * 10
        )
        if ok and new_name:
            bw.calculation_setups[new_name] = bw.calculation_setups[current].copy()
            # print("Current setups:", list(bw.calculation_setups.keys()))
            del bw.calculation_setups[current]
            # print("After deletion of {}:".format(current), list(bw.calculation_setups.keys()))
            signals.calculation_setup_selected.emit(new_name)
            print("Renamed calculation setup from {} to {}".format(current, new_name))

# ACTIVITY
    def new_activity(self, database_name):
        # TODO: let user define product
        name, ok = QtWidgets.QInputDialog.getText(
            None,
            "Create new technosphere activity",
            "Please specify an activity name:" + " " * 10,
        )
        if ok and name:
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
            signals.open_activity_tab.emit(new_act.key)
            signals.metadata_changed.emit(new_act.key)
            signals.database_changed.emit(database_name)
            signals.databases_changed.emit()

    def delete_activity(self, key):
        act = bw.get_activity(key)
        bw.database = act['database']
        nu = len(act.upstream())
        if nu:
            text = "activities consume" if nu > 1 else "activity consumes"
            QtWidgets.QMessageBox.information(
                None,
                "Not possible.",
                """Can't delete {}. {} upstream {} its reference product.
                Upstream exchanges must be modified or deleted.""".format(act, nu, text)
            )
        else:
            act.delete()
            signals.metadata_changed.emit(act.key)
            signals.database_changed.emit(act['database'])
            signals.databases_changed.emit()

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

    def duplicate_activity(self, key):
        """duplicates the selected activity in the same db, with a new BW code
        for creating a copy in a different db, use copy_to_db"""
        # todo: add "copy of" (or similar) to name of activity for easy identification in new db
        # todo: some interface feedback so user knows the copy has succeeded
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
        signals.metadata_changed.emit(new_act.key)
        signals.database_changed.emit(act['database'])
        signals.databases_changed.emit()
        signals.open_activity_tab.emit(new_act.key)

    def show_duplicate_to_db_interface(self, activity_key):
        origin_db = activity_key[0]
        activity = bw.get_activity(activity_key)

        available_target_dbs = bc.get_editable_databases()

        if origin_db in available_target_dbs:
            available_target_dbs.remove(origin_db)

        if not available_target_dbs:
            QtWidgets.QMessageBox.information(
                None,
                "No target database",
                "No valid target databases available. Create a new database or set one to writable (not read-only)."
            )
        else:
            target_db, ok = QtWidgets.QInputDialog.getItem(
                None,
                "Copy activity to database",
                "Target database:",
                available_target_dbs,
                0,
                False
            )
            if ok:
                self.duplicate_activity_to_db(target_db, activity)

    def duplicate_activity_to_db(self, target_db, activity):
        new_code = self.generate_copy_code((target_db, activity['code']))
        new_act_key = (target_db, new_code)
        activity.copy(code=new_code, database=target_db)
        # only process database immediately if small
        if len(bw.Database(target_db)) < 50:
            bw.databases.clean()

        signals.metadata_changed.emit(new_act_key)
        signals.database_changed.emit(target_db)
        signals.open_activity_tab.emit(new_act_key)
        signals.databases_changed.emit()

    def modify_activity(self, key, field, value):
        activity = bw.get_activity(key)
        activity[field] = value
        activity.save()
        signals.metadata_changed.emit(key)
        signals.database_changed.emit(key[0])

    # def modify_exchanges_output(self, exchanges, key):
    #     db_changed = {key[0]}
    #     for exc in exchanges:
    #         db_changed.add(exc['output'][0])
    #         if exc['type'] == 'production':
    #             new_exc = Exchange()
    #             new_exc._data = copy.deepcopy(exc._data)
    #             new_exc['type'] = 'technosphere'
    #             new_exc['output'] = key
    #             new_exc.save()
    #         else:
    #             exc['output'] = key
    #             exc.save()
    #     for db in db_changed:
    #         signals.database_changed.emit(db)

    def add_exchanges(self, from_keys, to_key):
        biosphere_types = ['emission', 'natural resource', 'social', 'economic']
        activity = bw.get_activity(to_key)
        for key in from_keys:
            from_act = bw.get_activity(key)
            exc = activity.new_exchange(input=key, amount=1)
            if key == to_key:
                exc['type'] = 'production'
            elif from_act.get('type', 'process') == 'process':
                exc['type'] = 'technosphere'
            elif from_act.get('type') in biosphere_types:
                exc['type'] = 'biosphere'
            else:
                exc['type'] = 'unknown'
            exc.save()
        signals.metadata_changed.emit(to_key)
        signals.database_changed.emit(to_key[0])


    def delete_exchanges(self, exchanges):
        db_changed = set()
        for exc in exchanges:
            db_changed.add(exc['output'][0])
            exc._document.delete_instance()
        for db in db_changed:
            # signals.metadata_changed.emit(to_key)
            signals.database_changed.emit(db)

    @staticmethod
    @pyqtSlot(object, str, object)
    def modify_exchange(exchange, field, value):
        exchange[field] = value
        # Never, ever, store an empty string in the formula field.
        if field == "formula" and value == "" and "formula" in exchange:
            del exchange[field]
        exchange.save()
        if field == "formula":
            signals.exchange_formula_changed.emit(exchange["output"])
        signals.database_changed.emit(exchange['output'][0])
