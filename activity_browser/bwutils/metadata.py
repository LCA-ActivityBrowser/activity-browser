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


def list_to_tuple(x) -> tuple:
    return tuple(x) if isinstance(x, list) else x


class MetaDataStore(QObject):
    """A container for technosphere and biosphere metadata during an AB session.

    This is to prevent multiple time-expensive repetitions such as the code
    below at various places throughout the AB:

    .. code-block:: python
        meta_data = list()  # or whatever container
        for ds in bw.Database(name):
            meta_data.append([ds[field] for field in fields])

    Instead, this data store features a dataframe that contains all metadata
    and can be indexed by (activity or biosphere key).
    The columns feature the metadata.

    Properties
    ----------
    index

    """
    # Options for reading classification systems from ecoinvent databases are
    # - ISIC rev.4 ecoinvent
    # - CPC
    # - EcoSpold01Categories
    # - HS (>= ecoinvent 3.10)
    # To show these columns in `ActivitiesBiosphereModel`,
    # add them to `self.act_fields` there and `CLASSIFICATION_SYSTEMS` below
    CLASSIFICATION_SYSTEMS = ["ISIC rev.4 ecoinvent"]

    synced: SignalInstance = Signal()

    def __init__(self, parent=None):
        from activity_browser import application
        super().__init__(parent)
        self.dataframe = pd.DataFrame()
        self.moveToThread(application.thread())
        self.connect_signals()

    def connect_signals(self):
        signals.project.changed.connect(self.sync)
        signals.node.changed.connect(self.on_node_changed)
        signals.node.deleted.connect(self.on_node_deleted)
        signals.meta.databases_changed.connect(self.sync_databases)
        signals.database.deleted.connect(self.sync_databases)

    def on_node_deleted(self, ds):
        try:
            self.dataframe.drop(ds.key, inplace=True)
            self.synced.emit()
        except KeyError:
            pass

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

    @property
    def databases(self):
        return set(self.dataframe.get("database", []))

    def sync_node(self, key: tuple) -> None:
        """Update metadata when an activity has changed.

        Three situations:
        1. An activity has been deleted.
        2. Activity data has been modified.
        3. An activity has been added.
           Note that duplicating activities is the same as adding a new activity.

        Parameters
        ----------
        key : tuple
            The specific activity to update in the MetaDataStore
        """
        data = self._get_node(key)
        if data is None:  # the activity has been deleted
            self.dataframe.drop(key, inplace=True)
        elif key in self.dataframe.index:  # the activity has been modified
            self.dataframe.loc[key] = data.loc[key]
        else:  # an activity has been added
            self.dataframe = pd.concat([self.dataframe, data], join="outer")

        self.thread().eventDispatcher().awake.connect(self._emitSyncLater, Qt.ConnectionType.UniqueConnection)

    def _emitSyncLater(self):
        t = time()
        self.synced.emit()
        log.debug(f"Metadatastore sync signal completed in {time() - t:.2f} seconds")
        self.thread().eventDispatcher().awake.disconnect(self._emitSyncLater)

    def _get_node(self, key: tuple):
        try:
            id = bd.mapping[key]
        except (UnknownObject, ActivityDataset.DoesNotExist):
            return None

        con = sqlite3.connect(sqlite3_lci_db._filepath)
        node_df = pd.read_sql(f"SELECT * FROM activitydataset WHERE id = {id}", con)
        con.close()

        return self._parse_df(node_df)

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

    def sync(self) -> None:
        """Deletes metadata when the project is changed."""
        log.debug("Synchronizing MetaDataStore")

        con = sqlite3.connect(sqlite3_lci_db._filepath)
        node_df = pd.read_sql("SELECT * FROM activitydataset", con)
        con.close()

        self.dataframe = self._parse_df(node_df)

        self.synced.emit()

    def _parse_df(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        data_df = pd.DataFrame([pickle.loads(x) for x in raw_df["data"]]).drop(columns=["id"], errors="ignore")

        df = raw_df.combine_first(data_df)
        df.drop(columns=["data"], inplace=True)

        df["key"] = df.loc[:, ["database", "code"]].apply(tuple, axis=1)
        if df.empty:
            return df
        df.index = pd.MultiIndex.from_tuples(df["key"])
        return df


    def get_existing_fields(self, field_list: list) -> list:
        """Return a list of fieldnames that exist in the current dataframe."""
        return [fn for fn in field_list if fn in self.dataframe.columns]

    def get_metadata(self, keys: list, columns: list) -> pd.DataFrame:
        """Return a slice of the dataframe matching row and column identifiers.

        NOTE: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#deprecate-loc-reindex-listlike
        From pandas version 1.0 and onwards, attempting to select a column
        with all NaN values will fail with a KeyError.
        """
        df = self.dataframe.loc[pd.IndexSlice[keys], :]
        return df.reindex(columns, axis="columns")

    def get_metadata_from_ids(self, ids: list, columns: list) -> pd.DataFrame:
        """Return a slice of the dataframe matching row and column identifiers.

        NOTE: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#deprecate-loc-reindex-listlike
        From pandas version 1.0 and onwards, attempting to select a column
        with all NaN values will fail with a KeyError.
        """
        df = self.dataframe.loc[self.dataframe["id"].isin(ids), :]
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

    @property
    def index(self):
        """Returns the (multi-) index of the MetaDataStore.

        This allows us to 'hide' the dataframe object in de AB_metadata
        """
        return self.dataframe.index

    def get_locations(self, db_name: str) -> set:
        """Returns a set of locations for the given database name."""
        data = self.get_database_metadata(db_name)
        if "location" not in data.columns:
            return set()
        locations = data["location"].unique()
        return set(locations[locations != ""])

    def get_units(self, db_name: str) -> set:
        """Returns a set of units for the given database name."""
        data = self.get_database_metadata(db_name)
        if "unit" not in data.columns:
            return set()
        units = data["unit"].unique()
        return set(units[units != ""])

    @lru_cache(maxsize=10)
    def get_tag_names_for_db(self, db_name: str) -> Set[str]:
        """Returns a set of tag names for the given database name."""
        data = self.get_database_metadata(db_name)
        if "tags" not in data.columns:
            return set()
        tags = data.tags.drop_duplicates().values
        tag_names = set(
            itertools.chain(*map(lambda x: x.keys(), filter(lambda x: x, tags)))
        )
        return tag_names

    def get_tag_names(self):
        """Returns a set of tag names for all databases."""
        tag_names = set()
        for db_name in self.databases:
            tag_names = tag_names.union(self.get_tag_names_for_db(db_name))
        return tag_names

    def print_convenience_information(self, db_name: str) -> None:
        """Reports how many unique locations and units the database has."""
        log.debug(
            "{} unique locations and {} unique units in {}".format(
                len(self.get_locations(db_name)), len(self.get_units(db_name)), db_name
            )
        )

    def unpack_classifications(self, df: pd.DataFrame, systems: list) -> pd.DataFrame:
        """Unpack classifications column to a new column for every classification system in 'systems'.

        Will return dataframe with added column.
        """
        classifications = list(df['classifications'].values)
        system_cols = []
        for system in systems:
            system_cols.append(self._unpacker(classifications, system))
        # creating the DF rotated is easier so we do that and then transpose
        unpacked = pd.DataFrame(system_cols, columns=df.index, index=systems).T

        # Finally, merge the df with the new unpacked df using indexes
        df = pd.merge(
            df, unpacked, how='inner', left_index=True,
            right_index=True, sort=False
        )
        return df

    def _unpacker(self, classifications: list, system: str) -> list:
        """Iterate over all 'c' lists in 'classifications'
        and add those matching 'system' to list 'system_classifications', when no matches, add empty string.
        If 'c' is not a list, add empty string.

        Always returns a list 'system_classifications' where len(system_classifications) == len(classifications).

        Testing showed that converting to list and doing the checks on a list is ~5x faster than keeping
        data in DF and using a df.apply() function, we do this now (difference was ~0.4s vs ~2s).
        """
        system_classifications = []
        for c in classifications:
            result = ""
            if not isinstance(c, (list, tuple, set)):
                system_classifications.append(result)
                continue
            for s in c:
                if s[0] == system:
                    result = s[1]
                    break
            system_classifications.append(result)  # result is either "" or the classification
        return system_classifications


AB_metadata = MetaDataStore()
