import sqlite3
import pickle
import os
from multiprocessing import Pool
from loguru import logger
from typing import Literal
import pandas as pd

from qtpy.QtCore import QObject, QThread, Signal, SignalInstance, Qt, Slot

from activity_browser.bwutils.settings import Settings

from .metadata import MetaDataStore
from .fields import secondary_types, primary, secondary, search_engine_whitelist, all_fields


class MDSLoader(QObject):
    """Load and refresh MetaDataStore from the Brightway LCI sqlite backend.

    Project-wide loads run at startup; :meth:`load_database` refreshes a single
    database after import. Reloads never block the GUI thread — concurrent
    requests are queued in :attr:`_pending_database_load`.
    """
    primary_status: Literal["idle", "loading", "done"] = "idle"
    secondary_status: Literal["idle", "loading", "done"] = "idle"

    def __init__(self, mds: MetaDataStore):
        super().__init__(parent=mds)

        self.mds = mds
        self.thread: QThread | None = None
        self._pending_database_load: str | None = None
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
        if self._has_cache() and Settings()["metadatastore"]["caching_enabled"]:
            self.cache_load_project()
            return

        # start loading thread for secondary metadata
        self.thread = SecondaryLoadThread(
            databases=list(bd.databases),
            sqlite_db=str(sqlite3_lci_db._filepath),
            parent=self,
        )
        self.thread.result.connect(self.secondary_load_project)
        self.thread.start()

        # load primary metadata in the main thread
        self.primary_load_project()

    def cache_load_project(self):
        from activity_browser.bwutils import filesystem

        logger.debug("Loading metadata from cache")

        cache_path = filesystem.get_project_ab_path() / "metadatastore_cache.pkl"
        try:
            cached_df = pd.read_pickle(cache_path)
        except (
            EOFError,
            ModuleNotFoundError,
            NotImplementedError,
            OSError,
            pickle.UnpicklingError,
            TypeError,
            ValueError,
        ) as exc:
            # NotImplementedError: pandas StringDtype / ndarray-backed columns can fail
            # to unpickle across pandas versions (see pandas GH issues on read_pickle).
            # ModuleNotFoundError: numpy 1.x vs 2.x pickles reference different internal modules
            # (e.g. numpy._core.numeric vs numpy.core.numeric).
            logger.warning(
                f"Metadata cache could not be loaded, rebuilding from database: {exc}"
            )
            cache_path.unlink(missing_ok=True)
            self.load_project()
            return

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

        searcher_thread = InitSearcherThread(self.mds, parent=self)
        searcher_thread.start()

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
        logger.debug("secondary_load_project")
        from bw2data.backends import sqlite3_lci_db

        if sqlite_db != str(sqlite3_lci_db._filepath):
            self.secondary_status = "done"
            return

        if secondary_df.empty:
            self.secondary_status = "done"
            return

        if not all(secondary_df.index.isin(self.mds.keys)):
            logger.debug("Secondary project metadata dropping rows")
            secondary_df = secondary_df[secondary_df.index.isin(self.mds.keys)]

        if secondary_df.empty:
            self.secondary_status = "done"
            return

        logger.debug(f"Secondary metadata loaded with {len(secondary_df)} rows")
        left = self.mds.get_metadata(columns=primary)

        self.mds.dataframe = pd.concat([left, secondary_df], axis=1)

        for idx in secondary_df.index:
            self.mds.register_mutation(idx, "update")
        
        self.secondary_status = "done"

        searcher_thread = InitSearcherThread(self.mds, parent=self)
        searcher_thread.start()

    def load_database(self, database_name: str):
        """Reload primary and secondary metadata for one database."""
        if self.thread is not None and self.thread.isRunning():
            logger.debug(
                "Metadata load already in progress, queueing reload for {!r}",
                database_name,
            )
            self._pending_database_load = database_name
            return

        self._start_database_load(database_name)

    def _start_database_load(self, database_name: str):
        from bw2data.backends import sqlite3_lci_db

        self._disconnect_thread_results()

        self.thread = SecondaryLoadThread(
            databases=[database_name],
            sqlite_db=str(sqlite3_lci_db._filepath),
            parent=self,
        )
        self.thread.result.connect(self.secondary_load_database)
        self.thread.finished.connect(self._on_load_thread_finished)
        self.thread.start()

        self.primary_load_database(database_name)

    def _disconnect_thread_results(self):
        if self.thread is None:
            return
        for slot in (self.secondary_load_project, self.secondary_load_database):
            try:
                self.thread.result.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        try:
            self.thread.finished.disconnect(self._on_load_thread_finished)
        except (TypeError, RuntimeError):
            pass

    def _on_load_thread_finished(self):
        pending = getattr(self, "_pending_database_load", None)
        if not pending:
            return
        self._pending_database_load = None
        self._start_database_load(pending)

    def primary_load_database(self, database_name: str):
        from bw2data.backends import sqlite3_lci_db

        with sqlite3.connect(sqlite3_lci_db._filepath) as con:
            fields = ', '.join(primary[1:])  # Exclude 'key' as it's constructed
            primary_df = pd.read_sql(f"SELECT {fields} FROM activitydataset WHERE database = '{database_name}'", con)

        primary_df["key"] = list(zip(primary_df["database"], primary_df["code"]))
        primary_df.index = pd.MultiIndex.from_tuples(primary_df["key"], names=["database", "code"])

        logger.debug(f"Primary metadata loaded with {len(primary_df)} rows")
        df = self.mds.dataframe
        if database_name in df.index.get_level_values(0):
            df = df.drop(database_name, level=0)
        self.mds.dataframe = pd.concat([df, primary_df])

        for idx in primary_df.index:
            self.mds.register_mutation(idx, "add")

        self.primary_status = "done"

    def secondary_load_database(self, secondary_df: pd.DataFrame, sqlite_db: str):
        from bw2data.backends import sqlite3_lci_db
        logger.debug("Starting secondary metadata load database callback")

        if secondary_df.empty or sqlite_db != str(sqlite3_lci_db._filepath):
            self.secondary_status = "done"
            return

        database = secondary_df.index[0][0]
        indices = self.mds.get_database_metadata(database, []).index

        if not all(secondary_df.index.isin(indices)):
            logger.debug("Secondary database metadata dropping rows")
            secondary_df = secondary_df[secondary_df.index.isin(indices)]

        logger.debug(f"Secondary metadata loaded with {len(secondary_df)} rows, adding to metadatastore {id(self.mds)}")

        df = self.mds.dataframe
        self._fix_categories(secondary_df, df)
        df = secondary_df.combine_first(df)
        self.mds.dataframe = df

        for idx in secondary_df.index:
            self.mds.register_mutation(idx, "update")

        if self.mds.searcher is not None:
            search_engine_cols = list(set(all_fields) & set(search_engine_whitelist))
            df = self.mds.get_database_metadata(database, search_engine_cols)
            for col in df.select_dtypes(include=['category']).columns:
                df[col] = df[col].astype(object)
            self.mds.searcher.add_identifier(df)

        self.secondary_status = "done"

    # utility functions
    @staticmethod
    def _fix_categories(df: pd.DataFrame, mds_df: pd.DataFrame):
        category_columns = [k for k, v in secondary_types.items() if v == "category"]

        for col in category_columns:
            categories = df[col].dropna().unique()
            categories = [c for c in categories if c not in mds_df[col].cat.categories]

            # add new category to column
            mds_df[col] = mds_df[col].cat.add_categories(categories)

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



class InitSearcherThread(QThread):
    """Thread for initializing the searcher."""

    def __init__(self, mds: MetaDataStore, parent):
        super().__init__(parent=parent)
        self.mds = mds

    def run(self):
        """Execute the searcher initialization in a background thread."""
        from .searcher import MDSSearcher

        if os.environ.get("AB_NO_SEARCHER"):
            logger.debug("Skipping searcher initialization due to AB_NO_SEARCHER environment variable")
            return

        if Settings()["metadatastore"]["searcher_enabled"] is False:
            logger.debug("Skipping searcher initialization due to settings")
            return

        if self.mds.searcher is not None:
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


class SecondaryLoadThread(QThread):
    """Thread for loading secondary metadata using multiprocessing Pool."""
    result: SignalInstance = Signal(pd.DataFrame, str)
    
    def __init__(self, databases: list[str], sqlite_db: str, parent):
        super().__init__(parent=parent)
        self.databases = databases
        self.sqlite_db = sqlite_db
    
    def run(self):
        """Execute the loading in a background thread."""
        try:
            if len(self.databases) > 1:
                logger.debug(f"Loading metadata from {len(self.databases)} databases using multiprocessing Pool")
                with Pool() as pool:
                    args = [(self.sqlite_db, db, secondary) for db in self.databases]
                    results = pool.starmap(load, args)
            else:
                logger.debug("Loading metadata from a single database without multiprocessing")
                results = [load(self.sqlite_db, db, secondary) for db in self.databases]

            full_df = pd.DataFrame()
            for df in results:
                if df is None or df.empty:
                    continue
                full_df = pd.concat([full_df, df])
            
        except Exception as e:
            logger.error(f"Error loading secondary metadata: {e}", exc_info=True)
            full_df = pd.DataFrame()

        self.result.emit(full_df, self.sqlite_db)


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


_reload_scheduler: "_DatabaseReloadScheduler | None" = None


class _DatabaseReloadScheduler(QObject):
    """Marshal single-database metadata reloads onto the Qt GUI thread."""

    reload_requested = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent=parent)
        self.reload_requested.connect(self._on_reload, Qt.QueuedConnection)

    @Slot(str)
    def _on_reload(self, db_name: str) -> None:
        from activity_browser import app

        app.metadata.loader.load_database(db_name)


def schedule_database_metadata_reload(db_name: str) -> None:
    """Queue a metadata reload on the Qt GUI thread.

    Safe to call from AB import worker threads (unlike ``QTimer.singleShot``).
    """
    from activity_browser import app

    global _reload_scheduler
    if _reload_scheduler is None:
        _reload_scheduler = _DatabaseReloadScheduler(parent=app.application)
    _reload_scheduler.reload_requested.emit(db_name)