# -*- coding: utf-8 -*-
from .signals import signals
from .ui.db_import_wizard import DatabaseImportWizard, DefaultBiosphereDialog
try:
    from . import settings
except ImportError:
    settings = None
import brightway2 as bw
from bw2data.backends.peewee import Exchange
from PyQt5 import QtWidgets
import copy
import uuid
from bw2data.project import ProjectDataset, create_database
import os


class Controller(object):
    def __init__(self, window):
        self.window = window
        signals.project_selected.emit(self.get_default_project_name())
        signals.calculation_setup_changed.connect(
            self.write_current_calculation_setup
        )
        self.connect_signals()
        self.db_wizard = None
        # switch directly to custom bw2 directory and project, if specified in settings
        print('Brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        print('Brightway2 active project: {}'.format(bw.projects.current))

        if settings:
            if hasattr(settings, "BW2_DIR"):
                self.switch_brightway2_dir_path(dirpath=settings.BW2_DIR)
                print('Switched to Brightway2 data directory: {}'.format(
                    bw.projects._base_data_dir))
            if hasattr(settings, "PROJECT_NAME"):
                if settings.PROJECT_NAME in [x.name for x in bw.projects]:
                    bw.projects.set_current(settings.PROJECT_NAME)
                    signals.project_selected.emit(settings.PROJECT_NAME)
                else:
                    print('Project indicated in settings.py not found.')

    def connect_signals(self):
        signals.copy_activity.connect(self.copy_activity)
        signals.activity_modified.connect(self.modify_activity)
        signals.new_activity.connect(self.new_activity)
        signals.exchanges_output_modified.connect(self.modify_exchanges_output)
        signals.exchanges_deleted.connect(self.delete_exchanges)
        signals.exchanges_add.connect(self.add_exchanges)
        signals.exchange_amount_modified.connect(self.modify_exchange_amount)
        signals.delete_activity.connect(self.delete_activity)
        signals.delete_activity.connect(self.delete_activity)
        signals.switch_bw2_dir_path.connect(self.select_bw2_dir_path)
        signals.import_database.connect(self.import_database_wizard)

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
            bw.projects.set_current("default")
            signals.project_selected.emit(self.get_default_project_name())
            # TODO: message to Statusbar
            print('Switched to {} as Brightway2 data directory.'.format(bw.projects._base_data_dir))

        except AssertionError:
            print('Could not access BW_DIR as specified in settings.py')

    def get_default_project_name(self):
        if "default" in bw.projects:
            return "default"
        else:
            return next(iter(bw.projects)).name

    def change_project(self):
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
            if name != bw.projects.current:
                bw.projects.set_current(name)
                signals.project_selected.emit(name)

    def new_project(self):
        name = self.window.dialog(
            "Create new project",
            "Name of new project:" + " " * 25
        )
        if name and name not in bw.projects:
            bw.projects.set_current(name)
            signals.project_selected.emit(name)
        elif name in bw.projects:
            # TODO feedback that project already exists
            pass

    def copy_project(self):
        name = self.window.dialog(
            "Copy current project",
            "Copy current project ({}) to new name:".format(bw.projects.current) + " " * 10
        )
        if name and name not in bw.projects:
            bw.projects.copy_project(name, switch=True)
            signals.project_selected.emit(name)

    def delete_project(self):
        if len(bw.projects) == 1:
            self.window.info("Can't delete last project")
            return
        ok = self.window.confirm((
            "Are you sure you want to delete project '{}'? It has {} databases"
            " and {} LCI methods").format(
            bw.projects.current,
            len(bw.databases),
            len(bw.methods)
        ))
        if ok:
            bw.projects.delete_project(bw.projects.current)
            signals.project_selected.emit(self.get_default_project_name())

    def install_default_data(self):
        self.default_biosphere_dialog = DefaultBiosphereDialog()

    def add_database(self):
        name = self.window.dialog(
            "Create new database",
            "Name of new database:" + " " * 25
        )
        if name:
            bw.Database(name).register()
            signals.databases_changed.emit()
            signals.database_selected.emit(name)

    def copy_database(self, name):
        name = self.window.right_panel.inventory_tab.databases.currentItem().db_name
        new_name = self.window.dialog(
            "Copy {}".format(name),
            "Name of new database:" + " " * 25)
        if new_name:
            bw.Database(name).copy(new_name)
            signals.databases_changed.emit()

    def delete_database(self, *args):
        name = self.window.right_panel.inventory_tab.databases.currentItem().db_name
        ok = self.window.confirm((
            "Are you sure you want to delete database '{}'? "
            "It has {} activity datasets").format(
            name,
            len(bw.Database(name))
        ))
        if ok:
            del bw.databases[name]
            signals.project_selected.emit(bw.projects.current)

    def new_calculation_setup(self):
        name = self.window.dialog(
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )
        if name:
            bw.calculation_setups[name] = {'inv': [], 'ia': []}
            signals.calculation_setup_selected.emit(name)

    def delete_calculation_setup(self):
        name = self.window.left_panel.cs_tab.list_widget.name
        del bw.calculation_setups[name]
        self.window.left_panel.cs_tab.set_default_calculation_setup()

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
        name = self.window.dialog(
            "Create new technosphere activity",
            "Name of new technosphere activity:" + " " * 10
        )
        if name:
            new_act = bw.Database(database_name).new_activity(
                code=uuid.uuid4().hex,
                name=name,
                unit="unit"
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
