try:
    from bw2data.backends.peewee.database import *
except ModuleNotFoundError:
    # we're running bw25
    from bw2data.backends.base import *

from activity_browser.mod.patching import patch_superclass, patched
from activity_browser.signals import (qactivity_list, qdatabase_list,
                                      qexchange_list)

from .proxies import Activity, ActivityDataset, Exchange, ExchangeDataset


@patch_superclass
class SQLiteBackend(SQLiteBackend):

    @property
    def changed(self):
        """
        Shorthand for connecting to the database QUpdater. Developers can instantiate a Database from bw2data and
        connect directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qdatabase_list.get_or_create(self).changed

    @property
    def deleted(self):
        """
        Shorthand for connecting to the database QUpdater. Developers can instantiate a Database from bw2data and
        connect directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qdatabase_list.get_or_create(self).deleted

    def delete(self, *args, **kwargs) -> None:
        # get all affected activities and exchanges that have QUpdater counterparts (i.e. have signals attached to them)
        acts = [
            (Activity(ActivityDataset.get_by_id(qact["id"])), qact)
            for qact in qactivity_list
            if qact["database"] == self.name
        ]

        excs = [
            (Exchange(ExchangeDataset.get_by_id(qexc["id"])), qexc)
            for qexc in qexchange_list
            if qexc["input_database"] == self.name
            or qexc["output_database"] == self.name
        ]

        # execute the patched function for standard functionality
        patched[SQLiteBackend]["delete"](self, *args, **kwargs)

        # emit the deleted db, affected activities, and affected exchanges
        [
            qdb.emitLater("changed", self)
            for qdb in qdatabase_list
            if qdb["name"] == self.name
        ]
        [
            qdb.emitLater("deleted", self)
            for qdb in qdatabase_list
            if qdb["name"] == self.name
        ]

        for act, qact in acts:
            qact.emitLater("changed", act)
        for act, qact in acts:
            qact.emitLater("deleted", act)

        for exc, qexc in excs:
            qexc.emitLater("changed", exc)
        for exc, qexc in excs:
            qexc.emitLater("deleted", exc)

    def get(self, code) -> Activity:
        return patched[SQLiteBackend]["get"](self, code)
