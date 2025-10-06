from logging import getLogger

import pandas as pd
import numpy as np
import timeit

from qtpy import QtCore

from activity_browser import signals, application

from .metadata import MetaDataStore
from .fields import primary, secondary, all_types

log = getLogger(__name__)


class MDSUpdater(QtCore.QObject):
    def __init__(self, mds: MetaDataStore):
        super().__init__(mds)
        self.moveToThread(application.thread())

        self.mds = mds
        self.connect_signals()

    def connect_signals(self):
        signals.node.changed.connect(self.on_node_changed)
        signals.node.deleted.connect(self.on_node_deleted)

        signals.meta.databases_changed.connect(self.on_database_changed)
        signals.database.deleted.connect(self.on_database_changed)

    # callbacks
    def on_node_changed(self, new, old):
        node_data = {f: getattr(new, f) for f in primary}
        node_data = node_data | {f: new.data.get(f, np.NaN) for f in secondary}
        node_data["key"] = new.key
        node_data = pd.Series(node_data, name=new.key)

        if new.key in self.mds.dataframe.index and not all(node_data.dropna().eq(self.mds.dataframe.loc[new.key].dropna())):
            self.modify_node(node_data)
        else:
            self.add_node(node_data)

    def on_node_deleted(self, ds):
        try:
            self.delete_node(ds)
        except KeyError:
            pass

    def on_database_changed(self) -> None:
        databases = databases_in_sqlite()

        for db_name in [x for x in self.mds.databases if x not in databases]:
            self.delete_database(db_name)

        for db_name in [x for x in databases if x not in self.mds.databases]:
            self.add_database(db_name)

    # node methods
    def modify_node(self, ds: pd.Series):
        self._fix_categories(ds)
        self.mds.dataframe.loc[ds.key] = ds
        self.mds.register_mutation(ds.key, "update")

    def add_node(self, ds: pd.Series):
        self._fix_categories(ds)
        self.mds.dataframe.loc[ds.key, :] = ds
        self.mds.register_mutation(ds.key, "add")

    def delete_node(self, ds: pd.Series):
        self.mds.dataframe = self.mds.dataframe.drop(ds.key)
        self.mds.register_mutation(ds.key, "delete")

    # database methods
    def add_database(self, db_name: str):
        self.mds.loader.load_database(db_name)

    def delete_database(self, db_name: str):
        for code in self.mds.dataframe.loc[db_name].index:
            self.mds.register_mutation((db_name, code), "delete")

        self.mds.dataframe = self.mds.dataframe.drop(db_name, level=0)

    # utility functions
    def _fix_categories(self, ds: pd.Series):
        for category_col in [k for k, v in all_types.items() if k in ds and v == "category"]:
            category = ds[category_col]

            if pd.isna(category):
                # cannot add NaN as a category
                continue

            if category in self.mds.dataframe[category_col].cat.categories:
                # category already exists
                continue

            # add new category to column
            self.mds.dataframe[category_col] = self.mds.dataframe[category_col].cat.add_categories([category])



def databases_in_sqlite() -> set[str]:
    import sqlite3
    from bw2data.backends import sqlite3_lci_db

    with sqlite3.connect(sqlite3_lci_db._filepath) as db:
        cursor = db.cursor()
        result = cursor.execute("SELECT DISTINCT database FROM activitydataset")

    return {x[0] for x in result}
