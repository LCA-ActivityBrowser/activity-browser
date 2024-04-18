from bw2data.backends.peewee.proxies import *

from activity_browser.signals import database_updater, activity_updater, exchange_updater
from activity_browser.brightway.patching import patch_superclass, patched
from bw2data import Database


@patch_superclass
class Exchanges(Exchanges):

    def delete(self):
        excs = list(self)
        acts = set()
        acts.update([exc.input for exc in excs])
        acts.update([exc.output for exc in excs])
        dbs = set([act["database"] for act in acts])

        patched().delete()

        for exc in excs:
            [qexc.emitLater("changed", exc) for qexc in exchange_updater if qexc["id"] == exc._document.id]
            [qexc.emitLater("deleted", exc) for qexc in exchange_updater if qexc["id"] == exc._document.id]

        for act in acts:
            [qact.emitLater("changed", act) for qact in activity_updater if qact["id"] == act._document.id]

        for db_name in dbs:
            [qdb.emitLater("changed", Database(db_name)) for qdb in database_updater if qdb["name"] == db_name]


@patch_superclass
class Activity(Activity):

    @property
    def changed(self):
        return activity_updater.get_or_create(self).changed

    @property
    def deleted(self):
        return activity_updater.get_or_create(self).deleted

    def save(self) -> None:
        from activity_browser.bwutils.metadata import AB_metadata
        patched().save()
        databases.set_modified(self["database"])
        AB_metadata.update_metadata(self.key)
        # exchanges cannot be changed through the activity proxy save function

        # emitting change through any existing qactivities (should be 1 or None)
        [qact.emitLater("changed", self) for qact in activity_updater if qact["id"] == self._document.id]

        # emitting change through an existing qdatabases (should be 1 or None)
        db = Database(self["database"])
        [qdb.emitLater("changed", db) for qdb in database_updater if qdb["name"] == self["database"]]

    def delete(self) -> None:
        from activity_browser.bwutils.metadata import AB_metadata
        patched().delete()
        databases.set_modified(self["database"])
        AB_metadata.update_metadata(self.key)
        # exchange deletions will emit for themselves

        # emitting change through any existing qactivities (should be 1 or None)
        [qact.emitLater("changed", self) for qact in activity_updater if qact["id"] == self._document.id]
        [qact.emitLater("deleted", self) for qact in activity_updater if qact["id"] == self._document.id]

        # emitting change through an existing qdatabases (should be 1 or None)
        db = Database(self["database"])
        [qdb.emitLater("changed", db) for qdb in database_updater if qdb["name"] == self["database"]]


@patch_superclass
class Exchange(Exchange):

    def __init__(self, document=None, **kwargs):
        patched().__init__(document, **kwargs)
        self.moved_IO = []

    @property
    def changed(self):
        return exchange_updater.get_or_create(self).changed

    @property
    def deleted(self):
        return exchange_updater.get_or_create(self).deleted

    def save(self) -> None:
        patched().save()

        # emitting change through any existing qexchanges (should be 1 or None)
        [qexc.emitLater("changed", self) for qexc in exchange_updater if qexc["id"] == self._document.id]

        # collecting unique activities and databases that have changed
        acts = set()
        dbs = set()

        acts.add(self.input)
        acts.add(self.output)
        acts.update(self.moved_IO)

        # emitting change through any existing qactivities
        for activity in acts:
            dbs.add(activity["database"])
            [qact.emitLater("changed", activity) for qact in activity_updater if qact["id"] == activity._document.id]

        # emitting change through any existing qdatabases
        for db_name in dbs:
            db = Database(db_name)
            [qdb.emitLater("changed", db) for qdb in database_updater if qdb["name"] == db_name]

        self.moved_IO.clear()

    def delete(self) -> None:
        patched().delete()

        # emitting change and deletion through any existing qexchanges (should be 1 or None)
        [qexc.emitLater("changed", self) for qexc in exchange_updater if qexc["id"] == self._document.id]
        [qexc.emitLater("deleted", self) for qexc in exchange_updater if qexc["id"] == self._document.id]

        # emitting change and deletion through any existing qactivities (should be 1 or None)
        [qact.emitLater("changed", self.input) for qact in activity_updater if qact["id"] == self.input._document.id]
        [qact.emitLater("changed", self.output) for qact in activity_updater if qact["id"] == self.output._document.id]

        in_db = Database(self.input["database"])
        [qdb.emitLater("changed", in_db) for qdb in database_updater if qdb["name"] == in_db.name]

        out_db = Database(self.output["database"])
        [qdb.emitLater("changed", out_db) for qdb in database_updater if qdb["name"] == out_db.name]
