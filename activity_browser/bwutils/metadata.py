# -*- coding: utf-8 -*-
import itertools
import sqlite3
import pickle
from time import time
from functools import lru_cache
from typing import Set
from logging import getLogger

from playhouse.shortcuts import model_to_dict

import pandas as pd

from qtpy.QtCore import Qt, QObject, Signal, SignalInstance

import bw2data as bd
from bw2data.errors import UnknownObject
from bw2data.backends import sqlite3_lci_db, ActivityDataset

from activity_browser import signals


log = getLogger(__name__)

class Fields:
    primary_types = {
        "id": int,
        "code": str,
        "database": "category",
        "location": "category",
        "name": str,
        "product": str,
        "type": "category",
    }
    secondary_types = {
        "synonyms": object,
        "unit": "category",
        "CAS number": "category",
        "categories": object,
        "processor": object,
    }
    all_types = {**primary_types, **secondary_types}

    primary = list(primary_types.keys())
    secondary = list(secondary_types.keys())
    all = primary + secondary


class MetaDataStore(QObject):
    synced: SignalInstance = Signal()

    def __init__(self, parent=None):
        from activity_browser import application
        super().__init__(parent)

        self._dataframe = pd.DataFrame(columns=Fields.all).astype(Fields.all_types)

        self.moveToThread(application.thread())
        self.loader = MDSLoader(self)

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @dataframe.setter
    def dataframe(self, df: pd.DataFrame) -> None:
        # Ensure all expected columns are present, in the correct order, and with the correct types
        df = df.reindex(columns=Fields.all)[Fields.all].astype(Fields.all_types)

        # Ensure the index is a MultiIndex with the correct names
        if not df.index.names == ["database", "code"]:
            df.index = df.index = pd.MultiIndex.from_frame(df[["database", "code"]])

        # Set the internal dataframe
        self._dataframe = df

        self.synced.emit()

    @property
    def databases(self):
        return set(self.dataframe.get("database", []))

    def _emitSyncLater(self):
        t = time()
        self.synced.emit()
        log.debug(f"Metadatastore sync signal completed in {time() - t:.2f} seconds")
        self.thread().eventDispatcher().awake.disconnect(self._emitSyncLater)

    def sync_databases(self) -> None:
        sync = False

        for db_name in [x for x in self.databases if x not in bd.databases]:
            # deleted databases
            self.dataframe.drop(db_name, level=0, inplace=True)
            sync = True

        for db_name in [x for x in bd.databases if x not in self.databases]:
            # new databases
            data = self._get_database(db_name)
            if data is None:
                continue

            if self.dataframe.empty:
                self.dataframe = data
            else:
                self.dataframe = pd.concat([self.dataframe, data], join="outer")

            sync = True

        if sync:
            self.thread().eventDispatcher().awake.connect(self._emitSyncLater, Qt.ConnectionType.UniqueConnection)

    def _get_database(self, db_name: str) -> pd.DataFrame | None:
        con = sqlite3.connect(sqlite3_lci_db._filepath)
        node_df = pd.read_sql(f"SELECT * FROM activitydataset WHERE database = '{db_name}'", con)
        con.close()
        if node_df.empty:
            return None
        return self._parse_df(node_df)

    def _parse_df(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        data_df = pd.DataFrame([pickle.loads(x) for x in raw_df["data"]]).drop(columns=["id"], errors="ignore")

        df = raw_df.combine_first(data_df)
        df.drop(columns=["data"], inplace=True)

        df["key"] = df.loc[:, ["database", "code"]].apply(tuple, axis=1)
        if df.empty:
            return df
        df.index = pd.MultiIndex.from_tuples(df["key"])
        return df

    def get_metadata(self, keys: list, columns: list) -> pd.DataFrame:
        """Return a slice of the dataframe matching row and column identifiers.

        NOTE: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#deprecate-loc-reindex-listlike
        From pandas version 1.0 and onwards, attempting to select a column
        with all NaN values will fail with a KeyError.
        """
        df = self.dataframe.loc[pd.IndexSlice[keys], :]
        return df.reindex(columns, axis="columns")

    def get_database_metadata(self, db_name: str) -> pd.DataFrame:
        """Return a slice of the dataframe matching the database.

        If the database does not exist in the metadata, attempt to add it.

        Parameters
        ----------
        db_name : str
            Name of the database to be retrieved

        Returns
        -------
        pd.DataFrame
            Slice of the metadata matching the database name

        """
        if db_name not in self.databases:
            return pd.DataFrame(columns=["name", "type", "location", "database", "code", "key", ])
        return self.dataframe.loc[self.dataframe["database"] == db_name].copy(deep=True).dropna(how='all', axis=1)


class MDSLoader:
    def __init__(self, mds: MetaDataStore):
        self.mds = mds
        self.connect_signals()
        self.primary_load_project()

    def connect_signals(self):
        signals.project.changed.connect(self.on_project_changed)
        #
        # signals.node.changed.connect(self.on_node_changed)
        # signals.node.deleted.connect(self.on_node_deleted)

        # signals.meta.databases_changed.connect(self.sync_databases)
        # signals.database.deleted.connect(self.sync_databases)

    def on_project_changed(self):
        self.primary_load_project()

    def on_node_changed(self, new, old):
        data_raw = model_to_dict(new)
        data = data_raw.pop("data")
        data.update(data_raw)
        data["key"] = new.key
        data = pd.DataFrame([data], index=pd.MultiIndex.from_tuples([new.key]))

        if new.key in self.dataframe.index:  # the activity has been modified

            compare_old = self.dataframe.loc[new.key].dropna().sort_index()
            compare_new = data.loc[new.key].dropna().sort_index()

            if list(compare_new.index) == list(compare_old.index) and (compare_new == compare_old).all():
                return  # but it is the same as the current DF, so no sync necessary
            for col in [col for col in data.columns if col not in self.dataframe.columns]:
                self.dataframe[col] = pd.NA
            self.dataframe.loc[new.key] = data.loc[new.key]
        elif self.dataframe.empty:  # an activity has been added and the dataframe was empty
            self.dataframe = data
        else:  # an activity has been added and needs to be concatenated to existing metadata
            self.dataframe = pd.concat([self.dataframe, data], join="outer")

        self.thread().eventDispatcher().awake.connect(self._emitSyncLater, Qt.ConnectionType.UniqueConnection)

    def on_node_deleted(self, ds):
        try:
            self.mds.dataframe = self.mds.dataframe.drop(ds.key, inplace=True)
        except KeyError:
            pass

    def primary_load_project(self):
        con = sqlite3.connect(sqlite3_lci_db._filepath)
        primary_df = pd.read_sql(f"SELECT {', '.join(Fields.primary)} FROM activitydataset", con)
        primary_df.index = pd.MultiIndex.from_frame(primary_df[["database", "code"]])
        con.close()

        self.mds.dataframe = pd.concat([self.mds.dataframe, primary_df])



AB_metadata = MetaDataStore()
