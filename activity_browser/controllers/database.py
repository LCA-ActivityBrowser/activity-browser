# -*- coding: utf-8 -*-
from typing import List

from bw2data.backends.peewee import SQLiteBackend
from bw2data import databases, Database
from PySide2.QtCore import QObject, Signal, SignalInstance

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata
from .activity import ABActivity, activity_controller


class DatabaseController(QObject):
    metadata_changed: SignalInstance = Signal()
    database_changed: SignalInstance = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.load()

        signals.project_selected.connect(self.load)

    # mimicking the iterable behaviour of bw2data.meta.databases
    def __getitem__(self, item) -> dict:
        return databases[item]

    def __iter__(self) -> dict:
        for database in databases:
            yield database

    def __delitem__(self, name) -> None:
        del databases[name]
        self.get(name).deleteLater()
        signals.delete_database_confirmed.emit(name)  # legacy
        signals.databases_changed.emit()

    # mirroring all public methods of bw2data.meta.databases
    def increment_version(self, database, number=None) -> None:
        databases.increment_version(database, number)
        self.metadata_changed.emit()

    def version(self, database):
        return databases.version(database)

    def set_modified(self, database) -> None:
        databases.set_modified(database)
        self.metadata_changed.emit()

    def set_dirty(self, database) -> None:
        databases.set_dirty(database)
        self.metadata_changed.emit()

    # extending functionality
    def load(self) -> None:
        for child in self.children():
            child.deleteLater()
        for db_name in databases:
            self.add(db_name)

    def get(self, database) -> "ABDatabase":
        return self.findChild(ABDatabase, database)

    def add(self, name) -> None:
        ABDatabase(name, self)
        self.metadata_changed.emit()
        signals.databases_changed.emit()  # legacy


class ABDatabase(QObject):
    data_changed: SignalInstance = Signal()
    deleted: SignalInstance = Signal()

    def __init__(self, name: str, parent: DatabaseController):
        super().__init__()

        # ABDatabases should live in the same thread as the DatabaseController (which is the main thread)
        self.moveToThread(parent.thread())
        self.setParent(parent)

        self.bw_database: SQLiteBackend = Database(name)
        self.bw_database.register()
        self.setObjectName(name)

        activity_controller.new_activity.connect(self._activity_link)
        activity_controller.activity_changed.connect(self._activity_link)
        activity_controller.activity_deleted.connect(self._activity_link)

    def __iter__(self) -> ABActivity:
        for activity in self.bw_database:
            yield ABActivity.from_activity(activity)

    def __len__(self) -> int:
        return len(self.bw_database)

    def _activity_link(self, activity) -> None:
        if activity["database"] != self.name: return
        self.data_changed.emit()

        # legacy
        signals.database_changed.emit(self.name)

    # mirroring database properties
    @property
    def name(self) -> str:
        return self.bw_database.name

    @property
    def backend(self) -> str:
        return self.bw_database.backend

    @property
    def filename(self) -> str:
        return self.bw_database.filename

    @property
    def order_by(self) -> str:
        return self.bw_database.order_by

    @property
    def registered(self) -> bool:
        return self.bw_database.registered

    @property
    def validator(self):
        return self.bw_database.validator

    def find_dependents(self, data=None, ignore=None) -> List[str]:
        return self.bw_database.find_dependents(data, ignore)

    def find_graph_dependents(self) -> List[str]:
        return self.bw_database.find_graph_dependents()

    # methods for database manipulation
    def copy(self, name) -> None:
        self.bw_database.copy(name)
        self.parent().add(name)

    def delete(self) -> None:
        self.bw_database.delete()
        self.deleted.emit()

    # methods returning activity proxies
    def random(self, filters=True, true_random=False) -> ABActivity:
        activity = self.bw_database.random(filters, true_random)
        return ABActivity.from_activity(activity)

    def get(self, code) -> ABActivity:
        activity = self.bw_database.get(code)
        return ABActivity.from_activity(activity)

    def new_activity(self, code, **kwargs) -> ABActivity:
        activity = self.bw_database.new_activity(code, **kwargs)
        activity.save()

        activity_controller.new_activity.emit(activity)

        # legacy
        AB_metadata.update_metadata(activity.key)
        signals.database_changed.emit(self.name)
        signals.databases_changed.emit()

        return ABActivity.from_activity(activity)

    def search(self, string, **kwargs) -> List[ABActivity]:
        result = self.bw_database.search(string, **kwargs)
        return [ABActivity.from_activity(activity) for activity in result]

    # methods directly changing data
    def write(self, data: dict):
        self.bw_database.write(data)
        for key in data.keys():
            # implement something like the following
            # activity_controller.changed.emit(key)
            return


database_controller = DatabaseController(application)
