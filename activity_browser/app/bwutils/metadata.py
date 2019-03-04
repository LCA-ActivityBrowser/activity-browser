# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
import numpy as np

from ..signals import signals
# todo: extend store over several projects


class MetaDataStore(object):
    """
A container for metadata for technosphere and biosphere activities during an AB session.

This is to prevent multiple time-expensive repetitions such as the code below at various places throughout the AB:

.. code-block:: python
    meta_data = list()  # or whatever container
    for ds in bw.Database(name):
        meta_data.append([ds[field] for field in fields])

Instead, this data store features a dataframe that contains all metadata and can be indexed by (activity or biosphere key). The columns feature the metadata.
    """
    def __init__(self):
        self.dataframe = pd.DataFrame()
        self.databases = set()
        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.reset_metadata)
        signals.metadata_changed.connect(self.update_metadata)


    def add_metadata(self, db_names_list):
        """Get metadata in form of a Pandas DataFrame for biosphere and technosphere databases
        for tables and additional aggregation.
        """
        dfs = list()
        dfs.append(self.dataframe)
        print('Current databases in the MetaDataStore:', self.databases)
        for db_name in db_names_list:
            if db_name not in bw.databases:
                raise ValueError('This database does not exist:', db_name)
            if db_name in self.databases:
                continue

            print('Adding:', db_name)
            self.databases.add(db_name)

            # make a temporary DataFrame and index it by ('database', 'code') (like all brightway activities)
            df_temp = pd.DataFrame(bw.Database(db_name))
            df_temp.index = pd.MultiIndex.from_tuples(zip(df_temp['database'], df_temp['code']))
            dfs.append(df_temp)
        self.dataframe = pd.concat(dfs, sort=False)
        self.dataframe.replace(np.nan, '', regex=True, inplace=True)  # replace 'nan' values with emtpy string
        print('Dimensions of the Metadata:', self.dataframe.shape)

    def update_metadata(self, key):
        """Update metadata when an activity has changed.
        Three situations:
        - Activity data has been modified.
        - An activity has been added.
        - An activity has been deleted."""
        try:
            print('Project:', bw.projects.current)
            print(type(key))
            act = bw.get_activity(key)  # if this does not work, it has been deleted (see except:).
        except:
            print('Deleting activity:', key)
            print(self.dataframe.shape)
            self.dataframe.drop([key])
            print('Dimensions of the Metadata:', self.dataframe.shape)
            return

        db = key[0]
        if db not in self.databases:
            print('Database has not been added to metadata.')
            self.add_metadata([db])
        else:
            if key in self.dataframe.index:  # activity has been modified and metadata needs to be updated
                print('Updating activity: ', act, key)
                for col in self.dataframe.columns:
                    self.dataframe.loc[key][col] = act.get(col, '')
            else:
                print('Adding activity:', act, key)
                df_new = pd.DataFrame([act.as_dict()], index=pd.MultiIndex.from_tuples([act.key]))
                self.dataframe = pd.concat([self.dataframe, df_new], sort=False)
                self.dataframe.replace(np.nan, '', regex=True, inplace=True)  # replace 'nan' values with emtpy string
            print('Dimensions of the Metadata:', self.dataframe.shape)

    def reset_metadata(self):
        """Deletes metadata when the project is changed."""
        # todo: metadata could be collected across projects...
        print('Reset metadata.')
        self.dataframe = pd.DataFrame()
        self.databases = set()


AB_metadata = MetaDataStore()