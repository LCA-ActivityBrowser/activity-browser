# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
import numpy as np

from ..signals import signals
# todo: extend store over several projects


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
    def __init__(self):
        self.dataframe = pd.DataFrame()
        self.databases = set()
        self._connect_signals()
        self.unpacked_columns = {}

    def _connect_signals(self):
        signals.project_selected.connect(self.reset_metadata)
        signals.metadata_changed.connect(self.update_metadata)

    def add_metadata(self, db_names_list):
        """"Include data from the brightway databases.

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
        dfs = list()
        dfs.append(self.dataframe)
        print('Current shape and databases in the MetaDataStore:', self.dataframe.shape, self.databases)
        for db_name in db_names_list:
            if db_name not in bw.databases:
                raise ValueError('This database does not exist:', db_name)
            if db_name in self.databases:
                continue

            print('Adding:', db_name)
            self.databases.add(db_name)

            # make a temporary DataFrame and index it by ('database', 'code') (like all brightway activities)
            df_temp = pd.DataFrame(bw.Database(db_name))

            # add keys and make MultiIndex from keys
            keys = [k for k in zip(df_temp['database'], df_temp['code'])]
            df_temp.index = pd.MultiIndex.from_tuples(keys)
            df_temp['key'] = keys

            # In a new 'biosphere3' database, some categories values are lists
            if 'categories' in df_temp:
                df_temp['categories'] = df_temp['categories'].apply(
                    lambda x: tuple(x) if isinstance(x, list) else x)

            dfs.append(df_temp)

        # add this metadata to already existing metadata
        self.dataframe = pd.concat(dfs, sort=False)
        self.dataframe.replace(np.nan, '', regex=True, inplace=True)  # replace 'nan' values with emtpy string
        # print('Dimensions of the Metadata:', self.dataframe.shape)

    def update_metadata(self, key):
        """Update metadata when an activity has changed.

        Three situations:
        1. An activity has been deleted.
        2. Activity data has been modified.
        3. An activity has been added.

        Parameters
        ----------
        key : str
            The specific activity to update in the MetaDataStore
        """
        try:
            act = bw.get_activity(key)  # if this does not work, it has been deleted (see except:).
        except:
            # Situation 1: activity has been deleted (metadata needs to be deleted)
            print('Deleting activity from metadata:', key)
            self.dataframe.drop(key, inplace=True)
            # print('Dimensions of the Metadata:', self.dataframe.shape)
            return

        db = key[0]
        if db not in self.databases:
            # print('Database has not been added to metadata.')
            self.add_metadata([db])
        else:
            if key in self.dataframe.index:  # Situation 2: activity has been modified (metadata needs to be updated)
                print('Updating activity in metadata: ', act, key)
                for col in self.dataframe.columns:
                    self.dataframe.at[key, col] = act.get(col, '')
                self.dataframe.at[key, 'key'] = act.key

            else:  # Situation 3: Activity has been added to database (metadata needs to be generated)
                print('Adding activity to metadata:', act, key)
                df_new = pd.DataFrame([act.as_dict()], index=pd.MultiIndex.from_tuples([act.key]))
                df_new['key'] = [act.key]
                self.dataframe = pd.concat([self.dataframe, df_new], sort=False)
                self.dataframe.replace(np.nan, '', regex=True, inplace=True)  # replace 'nan' values with emtpy string
            # print('Dimensions of the Metadata:', self.dataframe.shape)

    def reset_metadata(self):
        """Deletes metadata when the project is changed."""
        # todo: metadata could be collected across projects...
        print('Reset metadata.')
        self.dataframe = pd.DataFrame()
        self.databases = set()

    def get_existing_fields(self, field_list):
        """Return a list of fieldnames that exist in the current dataframe.
        """
        return [fn for fn in field_list if fn in self.dataframe.columns]

    def get_metadata(self, keys, columns):
        """Return a slice of the dataframe matching row and column identifiers.
        """
        return self.dataframe.loc[keys][columns]

    def get_database_metadata(self, db_name):
        """Return a slice of the dataframe matching the database.
        """
        return self.dataframe[self.dataframe['database'] == db_name]

    @property
    def index(self):
        """Returns the (multi-) index of the MetaDataStore.

        This allows us to 'hide' the dataframe object in de AB_metadata
        """
        return self.dataframe.index

    def unpack_tuple_column(self, colname, new_colnames=None):
        """Takes the given column in the dataframe and unpack it.

        To allow for quick aggregation, we:
        - Take the given column (eg: 'categories')
        - Find the max amount of values present for any row in that column,
          this is the amount of additional columns to generate.
        - Unpack the tuples of each row into separate column (using pd.Series)
        - Append the newly created columns to the MetaData dataframe
        """
        amount_columns = self.dataframe[colname].apply(len).max()

        if new_colnames is None:
            new_colnames = ["{}_{}".format(colname, x) for x in range(amount_columns)]

        # Check that the dataframe does not already contain the names
        # If this fails, print a warning and return.
        if colname in self.unpacked_columns:
            print("WARNING: Decomposed columns of {} already exist, aborting merge".format(colname))
            return

        # Generate a dataframe where the tuple is expanded to a series and
        # NaN values become empty strings
        unpacked = self.dataframe[colname].apply(
            lambda x: pd.Series([item for item in x])
        ).fillna('')

        # Give the columns the correct names
        unpacked.rename(
            columns={
                unpacked.columns[x]: new_colnames[x] for x in unpacked.columns
            }, inplace=True
        )

        # Finally, merge self.dataframe with the decomposed dataframe
        # using indexes
        self.dataframe = pd.merge(
            self.dataframe, unpacked, how='inner', left_index=True,
            right_index=True, sort=False
        )

        self.unpacked_columns[colname] = new_colnames


AB_metadata = MetaDataStore()
