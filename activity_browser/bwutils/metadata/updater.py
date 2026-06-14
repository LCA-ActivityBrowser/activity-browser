from loguru import logger

import pandas as pd
import numpy as np

from qtpy.QtCore import QObject

from .metadata import MetaDataStore
from .fields import primary, secondary, all_types, search_engine_whitelist


class MDSUpdater(QObject):

    def __init__(self, mds: MetaDataStore):
        super().__init__(parent=mds)
        self.mds = mds
        self.connect_signals()

    def connect_signals(self):
        from bw2data import signals
        from bw2data.meta import databases
        
        # Connect to Brightway signals
        signals.signaleddataset_on_save.connect(self.on_signaleddataset_save)
        signals.signaleddataset_on_delete.connect(self.on_signaleddataset_delete)
        signals.on_database_delete.connect(self.on_database_deleted_bw)
        databases._save_signal.connect(self.on_databases_metadata_change)

    # callbacks
    def on_signaleddataset_save(self, sender, old, new):
        """Called when a dataset is created or modified in Brightway."""
        from bw2data.backends import ActivityDataset
        
        # Only process ActivityDataset (nodes), not exchanges or parameters
        if not isinstance(new, ActivityDataset):
            return
            
        node_data = {f: getattr(new, f) for f in primary}
        node_data = node_data | {f: new.data.get(f, np.nan) for f in secondary}
        node_data["key"] = new.key
        node_data = pd.Series(node_data, name=new.key)

        if new.key in self.mds.dataframe.index and not all(node_data.dropna().eq(self.mds.dataframe.loc[new.key].dropna())):
            self.modify_node(node_data)
        elif new.key not in self.mds.dataframe.index:
            self.add_node(node_data)

    def on_signaleddataset_delete(self, sender, old):
        """Called when a dataset is deleted in Brightway."""
        from bw2data.backends import ActivityDataset
        
        # Only process ActivityDataset (nodes), not exchanges or parameters
        if not isinstance(old, ActivityDataset):
            return
            
        try:
            # Create a Series with the key to match the delete_node signature
            ds = pd.Series({"key": old.key, "id": old.id}, name=old.key)
            self.delete_node(ds)
        except KeyError:
            pass

    def on_database_deleted_bw(self, sender, name):
        """Called when a database is deleted in Brightway."""
        self.delete_database(name)
    
    def on_databases_metadata_change(self, sender, old, new):
        """Called when the databases metadata changes (e.g., new database added)."""
        self.on_database_changed()

    def on_database_changed(self) -> None:
        databases = databases_in_sqlite()

        for db_name in [x for x in self.mds.databases if x not in databases]:
            self.delete_database(db_name)

        for db_name in [x for x in databases if x not in self.mds.databases]:
            self.add_database(db_name)

    # node methods
    def modify_node(self, ds: pd.Series):
        df = self.mds.dataframe
        self._fix_categories(ds, df)
        df.loc[ds.key] = ds

        self.mds.dataframe = df
        self.mds.register_mutation(ds.key, "update")

        if not hasattr(self.mds, "searcher") or self.mds.searcher is None:
            return

        search_engine_cols = list(set(ds.keys()) & set(search_engine_whitelist))  # intersection becomes columns
        data = pd.DataFrame([ds[search_engine_cols]])
        self.mds.searcher.change_identifier(identifier=ds["id"], data=data)

    def add_node(self, ds: pd.Series):

        df = self.mds.dataframe
        self._fix_categories(ds, df)
        df.loc[ds.key, :] = ds

        self.mds.dataframe = df
        self.mds.register_mutation(ds.key, "add")

        if self.mds.searcher is None:
            return

        search_engine_cols = list(set(ds.keys()) & set(search_engine_whitelist))  # intersection becomes columns
        data = pd.DataFrame([ds[search_engine_cols]])
        self.mds.searcher.add_identifier(data=data)

    def delete_node(self, ds: pd.Series):
        self.mds.dataframe = self.mds.dataframe.drop(ds.key)
        self.mds.register_mutation(ds.key, "delete")

        if self.mds.searcher is None:
            return

        node_id = ds["id"]

        self.mds.searcher.remove_identifier(identifier=node_id)
        self.mds.searcher.reset_all_caches([ds.key[0]])

    # database methods
    def add_database(self, db_name: str):
        self.mds.loader.load_database(db_name)

    def delete_database(self, db_name: str):
        if db_name not in self.mds.databases:
            return

        for code in self.mds.dataframe.loc[db_name].index:
            self.mds.register_mutation((db_name, code), "delete")

        self.mds.dataframe = self.mds.dataframe.drop(db_name, level=0)

        if self.mds.searcher is None:
            return

        self.mds.searcher.remove_database(db_name)

    # utility functions
    @staticmethod
    def _fix_categories(ds: pd.Series, mds_df: pd.DataFrame):
        for category_col in [k for k, v in all_types.items() if k in ds and v == "category"]:
            category = ds[category_col]

            if pd.isna(category):
                # cannot add NaN as a category
                continue

            if category in mds_df[category_col].cat.categories:
                # category already exists
                continue

            # add new category to column
            mds_df[category_col] = mds_df[category_col].cat.add_categories([category])



def databases_in_sqlite() -> set[str]:
    import sqlite3
    from bw2data.backends import sqlite3_lci_db

    with sqlite3.connect(sqlite3_lci_db._filepath) as db:
        cursor = db.cursor()
        result = cursor.execute("SELECT DISTINCT database FROM activitydataset")

    return {x[0] for x in result}
