# -*- coding: utf-8 -*-
from logging import getLogger

import numpy as np
import pandas as pd
from bw2data.errors import UnknownObject

import activity_browser.bwutils.commontasks as bc
from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2data.backends import ActivityDataset

# todo: extend store over several projects

log = getLogger(__name__)


def list_to_tuple(x) -> tuple:
    return tuple(x) if isinstance(x, list) else x


class MetaDataStore(object):
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

    def __init__(self):
        self.dataframe = pd.DataFrame()
        self.databases = set()

        bd.projects.current_changed.connect(self.reset_metadata)
        bd.databases.metadata_changed.connect(self.check_databases)

    def add_metadata(self, db_names_list: list) -> None:
        """Include data from the brightway databases.

        Get metadata in form of a Pandas DataFrame for biosphere and
        technosphere databases for tables and additional aggregation.

        Parameters
        ----------
        db_names_list : list
            Contains the names of all databases to add to the MetaDataStore

        Raises
        ------
        ValueError
            If a database name does not exist in `brightway.databases`

        """
        new = set(db_names_list).difference(self.databases)
        if not new:
            return

        dfs = list()
        dfs.append(self.dataframe)
        log.debug(
            f"Current shape and databases in the MetaDataStore: {self.dataframe.shape} {self.databases}"
        )
        for db_name in new:
            if db_name not in bd.databases:
                raise ValueError("This database does not exist:", db_name)

            log.debug(f"Adding: {db_name}")
            self.databases.add(db_name)

            # make a temporary DataFrame and index it by ('database', 'code') (like all brightway activities)
            df = pd.DataFrame(bd.Database(db_name))
            df["key"] = df.loc[:, ["database", "code"]].apply(tuple, axis=1)
            df.index = pd.MultiIndex.from_tuples(df["key"])

            # add unpacked classifications columns if classifications are present
            if "classifications" in df.columns:
                df = self.unpack_classifications(df, self.CLASSIFICATION_SYSTEMS)

            # In a new 'biosphere3' database, some categories values are lists
            if "categories" in df.columns:
                df["categories"] = df.loc[:, "categories"].apply(list_to_tuple)

            dfs.append(df)

        # add this metadata to already existing metadata
        self.dataframe = pd.concat(dfs, sort=False)
        self.dataframe.replace(
            np.nan, "", regex=True, inplace=True
        )  # replace 'nan' values with emtpy string
        # print('Dimensions of the Metadata:', self.dataframe.shape)

    def update_metadata(self, key: tuple) -> None:
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
        try:
            act = bd.get_activity(
                key
            )  # if this does not work, it has been deleted (see except:).
        except (UnknownObject, ActivityDataset.DoesNotExist):
            # Situation 1: activity has been deleted (metadata needs to be deleted)
            log.debug(f"Deleting activity from metadata: {key}")
            self.dataframe.drop(key, inplace=True, errors="ignore")
            # print('Dimensions of the Metadata:', self.dataframe.shape)
            return

        db = key[0]
        if db not in self.databases:
            # print('Database has not been added to metadata.')
            self.add_metadata([db])
        else:
            if (
                key in self.dataframe.index
            ):  # Situation 2: activity has been modified (metadata needs to be updated)
                log.debug(f"Updating activity in metadata: {key}")
                for col in self.dataframe.columns:
                    if col in self.CLASSIFICATION_SYSTEMS:
                        # update classification data
                        classification = self._unpacker(
                            classifications=[act.get('classifications', '')],
                            system=col)
                        self.dataframe.at[key, col] = classification[0]
                    else:
                        self.dataframe.at[key, col] = act.get(col, '')
                self.dataframe.at[key, 'key'] = act.key

            else:  # Situation 3: Activity has been added to database (metadata needs to be generated)
                log.debug(f'Adding activity to metadata: {key}')
                df_new = pd.DataFrame([act.as_dict()], index=pd.MultiIndex.from_tuples([act.key]))
                df_new['key'] = [act.key]
                if act.get('classifications', False):  # add classification data if present
                    df_new = self.unpack_classifications(df_new, self.CLASSIFICATION_SYSTEMS)
                self.dataframe = pd.concat([self.dataframe, df_new], sort=False)
                self.dataframe.replace(
                    np.nan, "", regex=True, inplace=True
                )  # replace 'nan' values with emtpy string
            # print('Dimensions of the Metadata:', self.dataframe.shape)

    def reset_metadata(self) -> None:
        """Deletes metadata when the project is changed."""
        # todo: metadata could be collected across projects...
        log.debug("Reset metadata.")
        self.dataframe = pd.DataFrame()
        self.databases = set()

    def check_databases(self):
        removed_dbs = [db for db in self.databases if db not in bd.databases]
        for db in removed_dbs:
            self.dataframe.drop(self.dataframe[self.dataframe.database == db].index, inplace=True)
            self.databases.remove(db)

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
            if bc.count_database_records(db_name) == 0:
                return pd.DataFrame()
            self.add_metadata([db_name])
        return self.dataframe.loc[self.dataframe["database"] == db_name].copy(deep=True)

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
