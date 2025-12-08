import sqlite3
import pickle
import threading
from multiprocessing import Pool
from loguru import logger
from typing import Literal, Callable

import pandas as pd

from .metadata import MetaDataStore
from .fields import secondary_types, primary, secondary, search_engine_whitelist, all_fields


class MDSLoader:
    primary_status: Literal["idle", "loading", "done"] = "idle"
    secondary_status: Literal["idle", "loading", "done"] = "idle"

    def __init__(self, mds: MetaDataStore):
        self.mds = mds
        self.connect_signals()

    def connect_signals(self):
        from bw2data import signals
        
        # Connect to Brightway's project_changed signal
        signals.project_changed.connect(self.on_project_changed)

    def on_project_changed(self, sender):
        """Called when the Brightway project changes."""
        self.load_project()

    def load_project(self):
        import bw2data as bd
        from bw2data.backends import sqlite3_lci_db
        # set statuses
        self.primary_status = "loading"
        self.secondary_status = "loading"

        # check for valid cache and load from it if available
        if self._has_cache():
            self.cache_load_project()
            return

        # start loading thread for secondary metadata
        thread = SecondaryLoadThread(
            databases=list(bd.databases),
            sqlite_db=str(sqlite3_lci_db._filepath),
            callback=self.secondary_load_project
        )
        thread.start()

        # load primary metadata in the main thread
        self.primary_load_project()

    def cache_load_project(self):
        from activity_browser.bwutils import filesystem

        logger.debug("Loading metadata from cache")

        cache_path = filesystem.get_project_ab_path() / "metadatastore_cache.pkl"
        cached_df = pd.read_pickle(cache_path)

        # quick sanity checks
        if not self._cache_check(cached_df):
            logger.info("Cache file is invalid or outdated, loading from database instead")
            cache_path.unlink()
            self.load_project()
            return

        self.mds.dataframe = cached_df

        for idx in self.mds.dataframe.index:
            self.mds.register_mutation(idx, "add")

        self.primary_status = "done"
        self.secondary_status = "done"

        thread = threading.Thread(target=self._init_searcher)
        thread.start()

    def primary_load_project(self):
        from bw2data.backends import sqlite3_lci_db

        with sqlite3.connect(sqlite3_lci_db._filepath) as con:
            fields = ', '.join(primary[1:])  # Exclude 'key' as it's constructed
            primary_df = pd.read_sql(f"SELECT {fields} FROM activitydataset", con)

        primary_df["key"] = list(zip(primary_df["database"], primary_df["code"]))
        primary_df.index = pd.MultiIndex.from_tuples(primary_df["key"], names=["database", "code"])

        logger.debug(f"Primary metadata loaded with {len(primary_df)} rows")
        self.mds.dataframe = primary_df

        for idx in primary_df.index:
            self.mds.register_mutation(idx, "add")
        
        self.primary_status = "done"

    def secondary_load_project(self, secondary_df: pd.DataFrame, sqlite_db: str):
        from bw2data.backends import sqlite3_lci_db

        if sqlite_db != str(sqlite3_lci_db._filepath):
            return

        assert all(secondary_df.index.isin(self.mds.dataframe.index))
        logger.debug(f"Secondary metadata loaded with {len(secondary_df)} rows")
        left = self.mds.dataframe[primary].copy(deep=True)
        self.mds.dataframe = pd.concat([left, secondary_df], axis=1)

        for idx in secondary_df.index:
            self.mds.register_mutation(idx, "update")
        
        self.secondary_status = "done"
        self._init_searcher()

    def load_database(self, database_name: str):
        from bw2data.backends import sqlite3_lci_db
        self.primary_status = "loading"
        self.secondary_status = "loading"

        # start loading thread for secondary metadata
        thread = SecondaryLoadThread(
            databases=[database_name],
            sqlite_db=str(sqlite3_lci_db._filepath),
            callback=self.secondary_load_database
        )
        thread.start()

        # load primary metadata in the main thread
        self.primary_load_database(database_name)

    def primary_load_database(self, database_name: str):
        from bw2data.backends import sqlite3_lci_db

        with sqlite3.connect(sqlite3_lci_db._filepath) as con:
            fields = ', '.join(primary[1:])  # Exclude 'key' as it's constructed
            primary_df = pd.read_sql(f"SELECT {fields} FROM activitydataset WHERE database = '{database_name}'", con)

        primary_df["key"] = list(zip(primary_df["database"], primary_df["code"]))
        primary_df.index = pd.MultiIndex.from_tuples(primary_df["key"], names=["database", "code"])

        logger.debug(f"Primary metadata loaded with {len(primary_df)} rows")
        self.mds.dataframe = pd.concat([self.mds.dataframe, primary_df])

        for idx in primary_df.index:
            self.mds.register_mutation(idx, "add")

        self.primary_status = "done"

    def secondary_load_database(self, secondary_df: pd.DataFrame, sqlite_db: str):
        from bw2data.backends import sqlite3_lci_db

        if secondary_df.empty or sqlite_db != str(sqlite3_lci_db._filepath):
            return

        database = secondary_df.index[0][0]
        indices = self.mds.dataframe.loc[[database]].index

        if not all(secondary_df.index.isin(indices)):
            logger.debug("Secondary database metadata dropping rows")
            secondary_df = secondary_df[secondary_df.index.isin(indices)]

        logger.debug(f"Secondary metadata loaded with {len(secondary_df)} rows")

        self._fix_categories(secondary_df)
        df_copy = self.mds.dataframe.copy(deep=True)
        df_copy.update(secondary_df)
        self.mds.dataframe = df_copy

        for idx in secondary_df.index:
            self.mds.register_mutation(idx, "update")

        if hasattr(self.mds, "searcher"):
            search_engine_cols = list(set(all_fields) & set(search_engine_whitelist))
            df = self.mds.dataframe.loc[self.mds.dataframe["database"] == database, search_engine_cols]
            self.mds.searcher.add_identifier(df)

        self.secondary_status = "done"

    # utility functions
    def _fix_categories(self, df: pd.DataFrame):
        category_columns = [k for k, v in secondary_types.items() if v == "category"]

        for col in category_columns:
            categories = df[col].dropna().unique()
            categories = [c for c in categories if c not in self.mds.dataframe[col].cat.categories]

            # add new category to column
            self.mds.dataframe[col] = self.mds.dataframe[col].cat.add_categories(categories)

    def _init_searcher(self):
        from .searcher import MDSSearcher

        if hasattr(self.mds, 'searcher') and self.mds.searcher is not None:
            old_searcher = self.mds.searcher
            self.mds.searcher = None

            # Clear large data structures
            if hasattr(old_searcher, 'df'):
                del old_searcher.df
            if hasattr(old_searcher, 'identifier_to_word'):
                del old_searcher.identifier_to_word
            if hasattr(old_searcher, 'word_to_identifier'):
                del old_searcher.word_to_identifier
            if hasattr(old_searcher, 'word_to_q_grams'):
                del old_searcher.word_to_q_grams
            if hasattr(old_searcher, 'q_gram_to_word'):
                del old_searcher.q_gram_to_word

            del old_searcher

        self.mds.searcher = MDSSearcher(self.mds)

    def _has_cache(self) -> bool:
        from activity_browser.bwutils import filesystem

        cache_path = filesystem.get_project_ab_path() / "metadatastore_cache.pkl"
        lci_path = filesystem.get_project_path() / "lci" / "databases.db"

        if not cache_path.exists() or not lci_path.exists():
            return False

        cache_mtime = cache_path.stat().st_mtime
        lci_mtime = lci_path.stat().st_mtime

        return cache_mtime >= lci_mtime

    def _cache_check(self, cached_df: pd.DataFrame) -> bool:
        import bw2data as bd
        from bw2data.backends import sqlite3_lci_db

        if not all(db in bd.databases for db in cached_df["database"].unique()):
            logger.warning("Cache file contains databases not in the current Brightway project")
            return False

        if not len(cached_df) == len(cached_df["id"].unique()):
            logger.warning("Cache file contains duplicate IDs")
            return False

        if cached_df.empty:
            logger.warning("Cache file is empty")
            return False

        with sqlite3.connect(sqlite3_lci_db._filepath) as con:
            cursor = con.cursor()
            cursor.execute("SELECT COUNT(*) FROM activitydataset")
            count = cursor.fetchone()[0]

        if count != len(cached_df):
            logger.warning("Cache file row count does not match database row count")
            return False

        return True



class SecondaryLoadThread(threading.Thread):
    """Thread for loading secondary metadata using multiprocessing Pool."""
    
    def __init__(self, databases: list[str], sqlite_db: str, callback: Callable):
        super().__init__(daemon=True)
        self.databases = databases
        self.sqlite_db = sqlite_db
        self.callback = callback
        self.result_df = None
    
    def run(self):
        """Execute the loading in a background thread."""
        try:
            with Pool() as pool:
                args = [(self.sqlite_db, db, secondary) for db in self.databases]
                results = pool.starmap(load, args)

            full_df = pd.DataFrame()
            for df in results:
                if df is None or df.empty:
                    continue
                full_df = pd.concat([full_df, df])

            # Store result and call callback
            self.result_df = full_df
            self.callback(full_df, self.sqlite_db)
            
        except Exception as e:
            logger.error(f"Error loading secondary metadata: {e}")
            # Call callback with empty dataframe on error
            self.callback(pd.DataFrame(), self.sqlite_db)


def load(fp: str, database_name: str, fields: list[str]):
    con = sqlite3.connect(fp)
    sql = f"SELECT data FROM activitydataset WHERE database = '{database_name}'"
    raw_df = pd.read_sql(sql, con)
    con.close()

    df = pd.DataFrame([pickle.loads(x) for x in raw_df["data"]])
    if df.empty:
        return df

    df["key"] = list(zip(df["database"], df["code"]))
    df.index = pd.MultiIndex.from_tuples(df["key"], names=["database", "code"])
    df = df.reindex(columns=fields)[fields]
    return df