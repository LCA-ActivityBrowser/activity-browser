import sqlite3
import pickle
from time import time
from logging import getLogger

import pandas as pd
import bw2data as bd
from bw2data.backends import sqlite3_lci_db
from playhouse.shortcuts import model_to_dict

from qtpy.QtCore import Qt, QObject, Signal, SignalInstance

from .fields import all, all_types

log = getLogger(__name__)


class MetaDataStore(QObject):
    synced: SignalInstance = Signal()

    def __init__(self, parent=None):
        from activity_browser import application
        from .loader import MDSLoader

        super().__init__(parent)

        self._dataframe = pd.DataFrame(columns=all)

        self.moveToThread(application.thread())
        self.loader = MDSLoader(self)

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._dataframe

    @dataframe.setter
    def dataframe(self, df: pd.DataFrame) -> None:
        # Ensure all expected columns are present, in the correct order, and with the correct types
        df = df.reindex(columns=all)[all].astype(all_types)
        df["key"] = list(zip(df["database"], df["code"]))
        df.index = pd.MultiIndex.from_tuples(df["key"], names=["database", "code"])

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

AB_metadata = MetaDataStore()
