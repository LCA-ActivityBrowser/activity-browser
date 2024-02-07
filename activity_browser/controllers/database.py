# -*- coding: utf-8 -*-
import brightway2 as bw
import bw2data as bd
from bw2data.backends.peewee import sqlite3_lci_db
from bw2data.parameters import Group
from PySide2 import QtWidgets
from PySide2.QtCore import QObject, Slot, Qt

from activity_browser import log, signals, project_settings, application
from .project import ProjectController
from ..bwutils import commontasks as bc
from ..bwutils.strategies import relink_exchanges_existing_db
from ..ui.widgets import (
    CopyDatabaseDialog, DatabaseLinkingDialog, DefaultBiosphereDialog,
    BiosphereUpdater, DatabaseLinkingResultsDialog, EcoinventVersionDialog
)
from ..ui.wizards.db_export_wizard import DatabaseExportWizard
from ..ui.wizards.db_import_wizard import DatabaseImportWizard
from ..info import __ei_versions__
from ..utils import sort_semantic_versions


class DatabaseController(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        signals.import_database.connect(self.import_database_wizard)
        signals.export_database.connect(self.export_database_wizard)
        signals.update_biosphere.connect(self.update_biosphere)
        signals.add_database.connect(self.add_database)
        signals.delete_database.connect(self.delete_database)
        signals.copy_database.connect(self.copy_database)
        signals.install_default_data.connect(self.install_default_data)
        signals.relink_database.connect(self.relink_database)

        signals.project_selected.connect(self.ensure_sqlite_indices)

    @property
    def databases(self) -> list[bd.backends.SQLiteBackend]:
        db = bd.databases
        return db

    @Slot(name="openImportWizard")
    def import_database_wizard(self) -> None:
        """Start the database import wizard."""
        wizard = DatabaseImportWizard(application.main_window)
        wizard.show()

    @Slot(name="openExportWizard")
    def export_database_wizard(self) -> None:
        wizard = DatabaseExportWizard(application.main_window)
        wizard.show()

    @Slot(name="fixBrokenIndexes")
    def ensure_sqlite_indices(self):
        """
        - fix for https://github.com/LCA-ActivityBrowser/activity-browser/issues/189
        - also see bw2data issue: https://bitbucket.org/cmutel/brightway2-data/issues/60/massive-sqlite-query-performance-decrease
        @LegacyCode?
        """
        if bw.databases and not sqlite3_lci_db._database.get_indexes('activitydataset'):
            log.info("creating missing sqlite indices")
            bw.Database(list(bw.databases)[-1])._add_indices()

    @Slot(name="bw2Setup")
    def install_default_data(self) -> None:

        # let user choose version
        version_dialog = EcoinventVersionDialog(application.main_window)
        if version_dialog.exec_() != EcoinventVersionDialog.Accepted: return
        version = version_dialog.options.currentText()

        dialog = DefaultBiosphereDialog(version[:3], application.main_window)  # only read Major/Minor part of version
        dialog.show()

    @Slot(name="updateBiosphereDialog")
    def update_biosphere(self) -> None:
        """ Open a popup with progression bar and run through the different
        functions for adding ecoinvent biosphere flows.
        """
        # warn user of consequences of updating
        warn_dialog = QtWidgets.QMessageBox.question(
            application.main_window, "Update biosphere3?",
            'Newer versions of the biosphere database may not\n'
            'always be compatible with older ecoinvent versions.\n'
            '\nUpdating the biosphere3 database cannot be undone!\n',
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Abort,
            QtWidgets.QMessageBox.Abort
        )
        if warn_dialog is not QtWidgets.QMessageBox.Ok: return

        # let user choose version
        version_dialog = EcoinventVersionDialog(application.main_window)
        if version_dialog.exec_() != EcoinventVersionDialog.Accepted: return
        version = version_dialog.options.currentText()

        # reduce biosphere update list up to the selected version
        sorted_versions = sort_semantic_versions(__ei_versions__, highest_to_lowest=False)
        ei_versions = sorted_versions[:sorted_versions.index(version) + 1]

        # show updating dialog
        dialog = BiosphereUpdater(ei_versions, application.main_window)
        dialog.show()

    @Slot(name="addDatabase")
    def add_database(self):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new database",
            "Name of new database:" + " " * 25
        )

        if ok and name:
            if name not in bw.databases:
                bw.Database(name).register()
                bw.Database(name).write({})  # write nothing to the database so we set a modified time
                project_settings.add_db(name, False)
                signals.databases_changed.emit()
                signals.database_selected.emit(name)
            else:
                QtWidgets.QMessageBox.information(
                    application.main_window, "Not possible", "A database with this name already exists."
                )

    @Slot(str, QObject, name="copyDatabaseAction")
    def copy_database(self, name: str) -> None:
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Copy {}".format(name),
            "Name of new database:" + " " * 25)
        if ok and new_name:
            try:
                # Attaching the created wizard to the class avoids the copying
                # thread being prematurely destroyed.
                copy_progress = CopyDatabaseDialog(application.main_window)
                copy_progress.show()
                copy_progress.begin_copy(name, new_name)
                project_settings.add_db(new_name, project_settings.db_is_readonly(name))
            except ValueError as e:
                QtWidgets.QMessageBox.information(application.main_window, "Not possible", str(e))

    @Slot(str, name="deleteDatabase")
    def delete_database(self, name: str) -> None:
        ok = QtWidgets.QMessageBox.question(
            application.main_window,
            "Delete database?",
            ("Are you sure you want to delete database '{}'? It has {} activity datasets").format(
                name, bc.count_database_records(name))
        )
        if ok == QtWidgets.QMessageBox.Yes:
            project_settings.remove_db(name)
            del bw.databases[name]
            Group.delete().where(Group.name == name).execute()
            ProjectController.change_project(bw.projects.current, reload=True)
            signals.delete_database_confirmed.emit(name)

    @Slot(str, name="relinkDatabase")
    def relink_database(self, db_name: str) -> None:
        """Relink technosphere exchanges within the given database."""
        db = bw.Database(db_name)
        depends = db.find_dependents()
        options = [(depend, bw.databases.list) for depend in depends]
        dialog = DatabaseLinkingDialog.relink_sqlite(db_name, options, application.main_window)
        relinking_results = dict()
        if dialog.exec_() == DatabaseLinkingDialog.Accepted:
            # Now, start relinking.
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            for old, new in dialog.relink.items():
                other = bw.Database(new)
                failed, succeeded, examples = relink_exchanges_existing_db(db, old, other)
                relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)
            QtWidgets.QApplication.restoreOverrideCursor()
            if failed > 0:
                QtWidgets.QApplication.restoreOverrideCursor()
                relinking_dialog = DatabaseLinkingResultsDialog.present_relinking_results(application.main_window, relinking_results, examples)
                relinking_dialog.exec_()
                activity = relinking_dialog.open_activity()
            QtWidgets.QApplication.restoreOverrideCursor()
            signals.database_changed.emit(db_name)
            signals.databases_changed.emit()

database_controller = DatabaseController(application)
