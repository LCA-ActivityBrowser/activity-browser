from bw2data.backends.peewee.database import *

from bw2data.backends.peewee.proxies import Activity, ActivityDataset, Exchange, ExchangeDataset

from activity_browser.signals import qdatabase_list, qactivity_list, qexchange_list
from activity_browser.brightway.patching import patch_superclass, patched


@patch_superclass
class SQLiteBackend(SQLiteBackend):

    @property
    def changed(self):
        return qdatabase_list.get_or_create(self).changed

    @property
    def deleted(self):
        return qdatabase_list.get_or_create(self).deleted

    @property
    def tag(self) -> str:
        return self.name

    def delete(self, keep_params=False, warn=True) -> None:
        # get all affected activities and exchanges that have virtual counterparts (i.e. have signals attached to them)
        acts = [(Activity(ActivityDataset.get_by_id(qact.id)), qact)
                for qact in qactivity_list
                if qact["database"] == self.name]

        excs = [(Exchange(ExchangeDataset.get_by_id(qexc.id)), qexc)
                for qexc in qexchange_list
                if qexc["input_database"] == self.name or qexc["output_database"] == self.name]

        patched().delete(keep_params, warn)

        # emit the deleted db, affected activities, and affected exchanges
        [qdb.emitLater("changed", self) for qdb in qdatabase_list if qdb["name"] == self.name]
        [qdb.emitLater("deleted", self) for qdb in qdatabase_list if qdb["name"] == self.name]

        for act, qact in acts: qact.emitLater("changed", act)
        for act, qact in acts: qact.emitLater("deleted", act)

        for exc, qexc in excs: qexc.emitLater("changed", exc)
        for exc, qexc in excs: qexc.emitLater("deleted", exc)

    def get(self, code) -> Activity:
        return patched().get(code)