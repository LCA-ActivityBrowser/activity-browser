# -*- coding: utf-8 -*-
from typing import Optional

import brightway2 as bw
from bw2data.backends.peewee import sqlite3_lci_db
from bw2data.parameters import Group
from PySide2 import QtWidgets
from PySide2.QtCore import QObject, Slot

from ..bwutils import commontasks as bc
from ..bwutils.strategies import relink_exchanges_existing_db
from ..ui.widgets import CopyDatabaseDialog, DatabaseLinkingDialog
from ..ui.wizards.db_import_wizard import DatabaseImportWizard, DefaultBiosphereDialog
from ..settings import project_settings
from ..signals import signals


class DatabaseController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent
        self.db_wizard: Optional[QtWidgets.QWizard] = None
        self.default_biosphere_dialog: Optional[QtWidgets.QDialog] = None
        self.copy_progress: Optional[QtWidgets.QDialog] = None

        signals.import_database.connect(self.import_database_wizard)
        signals.add_database.connect(self.add_database)
        signals.delete_database.connect(self.delete_database)
        signals.copy_database.connect(self.copy_database)
        signals.install_default_data.connect(self.install_default_data)
        signals.relink_database.connect(self.relink_database)

        signals.change_project.connect(self.clear_database_wizard)
        signals.project_selected.connect(self.ensure_sqlite_indices)

    @Slot(name="deleteDatabaseWizard")
    def clear_database_wizard(self):
        """ Separate cleanup method, used to clear out existing import wizard
        when switching projects.
        """
        if self.db_wizard is None:
            return
        self.db_wizard.deleteLater()
        self.db_wizard = None

    @Slot(QObject, name="openImportWizard")
    def import_database_wizard(self, parent):
        """ Create a database import wizard, if it already exists, set the
        previous one to delete and recreate it.
        """
        self.clear_database_wizard()
        self.db_wizard = DatabaseImportWizard(parent)

    @Slot(name="fixBrokenIndexes")
    def ensure_sqlite_indices(self):
        """
        - fix for https://github.com/LCA-ActivityBrowser/activity-browser/issues/189
        - also see bw2data issue: https://bitbucket.org/cmutel/brightway2-data/issues/60/massive-sqlite-query-performance-decrease
        @LegacyCode?
        """
        if bw.databases and not sqlite3_lci_db._database.get_indexes('activitydataset'):
            print("creating missing sqlite indices")
            bw.Database(list(bw.databases)[-1])._add_indices()

    @Slot(name="bw2Setup")
    def install_default_data(self):
        self.default_biosphere_dialog = DefaultBiosphereDialog()
        project_settings.add_db("biosphere3")

    @Slot(name="addDatabase")
    def add_database(self):
        name, ok = QtWidgets.QInputDialog.getText(
            self.window,
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
                QtWidgets.QMessageBox.information(
                    self.window, "Not possible", "A database with this name already exists."
                )

    @Slot(str, QObject, name="copyDatabaseAction")
    def copy_database(self, name, parent):
        new_name, ok = QtWidgets.QInputDialog.getText(
            parent,
            "Copy {}".format(name),
            "Name of new database:" + " " * 25)
        if ok and new_name:
            try:
                # Attaching the created wizard to the class avoids the copying
                # thread being prematurely destroyed.
                self.copy_progress = CopyDatabaseDialog(parent)
                self.copy_progress.begin_copy(name, new_name)
                project_settings.add_db(new_name)
            except ValueError as e:
                QtWidgets.QMessageBox.information(parent, "Not possible", str(e))

    @Slot(str, name="deleteDatabase")
    def delete_database(self, name: str) -> None:
        ok = QtWidgets.QMessageBox.question(
            self.window,
            "Delete database?",
            ("Are you sure you want to delete database '{}'? It has {} activity datasets").format(
                name, bc.count_database_records(name))
        )
        if ok == QtWidgets.QMessageBox.Yes:
            project_settings.remove_db(name)
            del bw.databases[name]
            Group.delete().where(Group.name == name).execute()
            self.change_project(bw.projects.current, reload=True)

    @Slot(str, QObject, name="relinkDatabase")
    def relink_database(self, db_name: str, parent: QObject) -> None:
        """Relink technosphere exchanges within the given database."""
        db = bw.Database(db_name)
        depends = db.find_dependents()
        options = [(depend, bw.databases.list) for depend in depends]
        dialog = DatabaseLinkingDialog.relink_sqlite(db_name, options, parent)
        if dialog.exec_() == DatabaseLinkingDialog.Accepted:
            # Now, start relinking.
            for old, new in dialog.relink.items():
                other = bw.Database(new)
                relink_exchanges_existing_db(db, old, other)
            signals.database_changed.emit(db_name)
            signals.databases_changed.emit()
