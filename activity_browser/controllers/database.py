from bw2data import databases
from PySide2.QtCore import QObject, Signal, SignalInstance

import activity_browser.bwutils.data as ABData
from activity_browser import application
from .base import VirtualDatapoint


class VirtualDatabase(VirtualDatapoint):
    changed = Signal(ABData.ABDatabase)
    deleted = Signal(ABData.ABDatabase)

    data_point: ABData.ABDatabase

    @property
    def name(self):
        return self.data_point.name if self.data_point else None


class DatabaseController(QObject):
    metadata_changed: SignalInstance = Signal()

    _dummy = VirtualDatabase()

    # mimicking the iterable behaviour of bw2data.meta.databases
    def __getitem__(self, item) -> dict:
        return databases[item]

    def __iter__(self) -> dict:
        for database in databases:
            yield database

    def __delitem__(self, name) -> None:
        ABData.ABDatabase(name).delete(warn=False)
        del databases[name]

        self.metadata_changed.emit()

    # extending functionality
    def sync(self) -> None:
        self.metadata_changed.emit()

    def get(self, database_name: str) -> ABData.ABDatabase:
        return ABData.ABDatabase(database_name)

    def get_virtual(self, database: ABData.ABDatabase, create=False):
        virtual_database = self.findChild(VirtualDatabase, database.name)

        if virtual_database: return virtual_database
        elif create: return VirtualDatabase(database.name, database, self)
        else: return self._dummy

    def changed(self, database: ABData.ABDatabase):
        virtual_database = self.findChild(VirtualDatabase, database.name)
        if not virtual_database: return
        virtual_database.changed.emit(database)

    def deleted(self, database: ABData.ABDatabase):
        virtual_database = self.findChild(VirtualDatabase, database.name)
        if not virtual_database: return
        virtual_database.deleted.emit(database)


database_controller = DatabaseController(application)