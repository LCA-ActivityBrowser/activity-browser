try:
    from bw2data.backends.peewee.proxies import *
except ModuleNotFoundError:
    # we're running bw25
    from bw2data.backends.proxies import *

from bw2data import Database, get_activity

from activity_browser.mod.patching import patch_superclass, patched
from activity_browser.signals import (qactivity_list, qdatabase_list,
                                      qexchange_list)


@patch_superclass
class Exchanges(Exchanges):

    def delete(self, allow_in_sourced_project: bool = False):
        # find only the exchanges that have qexchange counterparts within ourselves
        exc_query = ExchangeDataset.id << [qexc["id"] for qexc in qexchange_list]
        exc_args = self._args + [exc_query]
        excs = [Exchange(doc) for doc in ExchangeDataset.select().where(*exc_args)]

        # find only the input or output activities that have qactivity counterparts

        # get all qactivity keys
        act_keys = [(qact["database"], qact["code"]) for qact in qactivity_list]

        # gather affected output activities

        # construct a preliminary query using only the output code (this should get us very far)
        act_query = ExchangeDataset.output_code << [key[1] for key in act_keys]

        # combine with the existing query
        act_args = self._args + [act_query]

        # execute query to a set, and only select activities that are in act_keys
        acts = {
            get_activity((doc.output_database, doc.output_code))
            for doc in ExchangeDataset.select().where(*act_args)
            if (doc.output_database, doc.output_code) in act_keys
        }

        # gather affected input activities

        # same process as above but for input_code and input_database
        act_query = ExchangeDataset.input_code << [key[1] for key in act_keys]
        act_args = self._args + [act_query]
        acts.update(
            {
                get_activity((doc.input_database, doc.input_code))
                for doc in ExchangeDataset.select().where(*act_args)
                if (doc.input_database, doc.input_code) in act_keys
            }
        )

        # use the activities set to create a database set as well
        dbs = set([act["database"] for act in acts])

        # execute the patched function for standard functionality
        patched[Exchanges]["delete"](self, allow_in_sourced_project)

        # emitting change through any existing exchange QUpdaters
        for exc in excs:
            [
                qexc.emitLater("changed", exc)
                for qexc in qexchange_list
                if qexc["id"] == exc._document.id
            ]
            [
                qexc.emitLater("deleted", exc)
                for qexc in qexchange_list
                if qexc["id"] == exc._document.id
            ]

        # emitting change through any existing activity QUpdaters
        for act in acts:
            [
                qact.emitLater("changed", act)
                for qact in qactivity_list
                if qact["id"] == act._document.id
            ]

        # emitting change through any existing database QUpdaters
        for db_name in dbs:
            [
                qdb.emitLater("changed", Database(db_name))
                for qdb in qdatabase_list
                if qdb["name"] == db_name
            ]


@patch_superclass
class Activity(Activity):

    @property
    def changed(self):
        """
        Shorthand for connecting to the activity QUpdater. Developers can instantiate an Activity from bw2data and
        connect directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qactivity_list.get_or_create(self).changed

    @property
    def deleted(self):
        """
        Shorthand for connecting to the activity QUpdater. Developers can instantiate an Activity from bw2data and
        connect directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qactivity_list.get_or_create(self).deleted

    def save(self, signal: bool = True, data_already_set: bool = False,
             force_insert: bool = False) -> None:
        from activity_browser.bwutils.metadata import AB_metadata

        # execute the patched function for standard functionality
        patched[Activity]["save"](self, signal, data_already_set, force_insert)

        # this is called already within the patched function, but needs to be recalled now the data is actually updated
        databases.set_modified(self["database"])

        # should eventually be replaced
        AB_metadata.update_metadata(self.key)

        # exchanges cannot be changed through the activity proxy save function

        # emitting change through any existing qactivities (should be 1 or None)
        [
            qact.emitLater("changed", self)
            for qact in qactivity_list
            if qact["id"] == self._document.id
        ]

        # emitting change through an existing qdatabases (should be 1 or None)
        db = Database(self["database"])
        [
            qdb.emitLater("changed", db)
            for qdb in qdatabase_list
            if qdb["name"] == self["database"]
        ]

    def delete(self, signal: bool = True):
        from activity_browser.bwutils.metadata import AB_metadata

        # execute the patched function for standard functionality
        patched[Activity]["delete"](self, signal)

        databases.set_modified(self["database"])

        # this is leading to a lot of calls and should eventually be dealt with
        AB_metadata.update_metadata(self.key)

        # exchange deletions will emit for themselves

        # emitting change through any existing qactivities (should be 1 or None)
        [
            qact.emitLater("changed", self)
            for qact in qactivity_list
            if qact["id"] == self._document.id
        ]
        [
            qact.emitLater("deleted", self)
            for qact in qactivity_list
            if qact["id"] == self._document.id
        ]

        # emitting change through an existing qdatabases (should be 1 or None)
        db = Database(self["database"])
        [
            qdb.emitLater("changed", db)
            for qdb in qdatabase_list
            if qdb["name"] == self["database"]
        ]


@patch_superclass
class Exchange(Exchange):

    def __init__(self, document=None, **kwargs):
        # execute the patched function for standard functionality
        patched[Exchange]["__init__"](self, document, **kwargs)

        # we need to keep track of changed input and output activities, as they will have to be signalled too when the
        # exchange is saved.
        self.moved_IO = []

    @property
    def changed(self):
        """
        Shorthand for connecting to the activity QUpdater. Developers can instantiate an Activity from bw2data and
        connect directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qexchange_list.get_or_create(self).changed

    @property
    def deleted(self):
        """
        Shorthand for connecting to the activity QUpdater. Developers can instantiate an Activity from bw2data and
        connect directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qexchange_list.get_or_create(self).deleted

    def save(self, signal: bool = True, data_already_set: bool = False,
             force_insert: bool = False):
        # execute the patched function for standard functionality
        patched[Exchange]["save"](self, signal, data_already_set, force_insert)

        # emitting change through any existing qexchanges (should be 1 or None)
        [
            qexc.emitLater("changed", self)
            for qexc in qexchange_list
            if qexc["id"] == self._document.id
        ]

        # collecting unique activities and databases that have changed
        acts = set()
        dbs = set()

        acts.add(self.input)
        acts.add(self.output)
        acts.update(self.moved_IO)

        # emitting change through any existing qactivities
        for activity in acts:
            dbs.add(activity["database"])
            [
                qact.emitLater("changed", activity)
                for qact in qactivity_list
                if qact["id"] == activity._document.id
            ]

        # emitting change through any existing qdatabases
        for db_name in dbs:
            db = Database(db_name)
            [
                qdb.emitLater("changed", db)
                for qdb in qdatabase_list
                if qdb["name"] == db_name
            ]

        self.moved_IO.clear()

    def delete(self, signal: bool = True):
        # execute the patched function for standard functionality
        patched[Exchange]["delete"](self, signal)

        # emitting change and deletion through any existing qexchanges (should be 1 or None)
        [
            qexc.emitLater("changed", self)
            for qexc in qexchange_list
            if qexc["id"] == self._document.id
        ]
        [
            qexc.emitLater("deleted", self)
            for qexc in qexchange_list
            if qexc["id"] == self._document.id
        ]

        # emitting change for any existing qactivities (should be 1 or None)
        [
            qact.emitLater("changed", self.input)
            for qact in qactivity_list
            if qact["id"] == self.input._document.id
        ]
        [
            qact.emitLater("changed", self.output)
            for qact in qactivity_list
            if qact["id"] == self.output._document.id
        ]

        # emitting change for related databases
        in_db = Database(self.input["database"])
        [
            qdb.emitLater("changed", in_db)
            for qdb in qdatabase_list
            if qdb["name"] == in_db.name
        ]

        out_db = Database(self.output["database"])
        [
            qdb.emitLater("changed", out_db)
            for qdb in qdatabase_list
            if qdb["name"] == out_db.name
        ]
