# -*- coding: utf-8 -*-
import brightway2 as bw
from bw2data.backends.peewee import sqlite3_lci_db
from bw2data.parameters import Group
from PySide2.QtCore import QObject, Slot

from activity_browser import log, signals, project_settings, application
from .project import ProjectController
from ..bwutils import commontasks as bc


class DatabaseController(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        signals.project_selected.connect(self.ensure_sqlite_indices)

    def ensure_sqlite_indices(self):
        """
        - fix for https://github.com/LCA-ActivityBrowser/activity-browser/issues/189
        - also see bw2data issue: https://bitbucket.org/cmutel/brightway2-data/issues/60/massive-sqlite-query-performance-decrease
        @LegacyCode?
        """
        if bw.databases and not sqlite3_lci_db._database.get_indexes('activitydataset'):
            log.info("creating missing sqlite indices")
            bw.Database(list(bw.databases)[-1])._add_indices()

    def new_database(self, name):
        assert name not in bw.databases

        bw.Database(name).register()
        bw.Database(name).write({})  # write nothing to the database so we set a modified time

        project_settings.add_db(name, False)
        signals.databases_changed.emit()
        signals.database_selected.emit(name)

    def duplicate_database(self, from_db: str, to_db: str) -> None:
        bw.Database(from_db).copy(to_db)
        signals.databases_changed.emit()

    def delete_database(self, name: str) -> None:
        project_settings.remove_db(name)
        del bw.databases[name]
        Group.delete().where(Group.name == name).execute()
        ProjectController.change_project(bw.projects.current, reload=True)
        signals.delete_database_confirmed.emit(name)

    @staticmethod
    def record_count(db_name: str) -> int:
        return bc.count_database_records(db_name)


database_controller = DatabaseController(application)
