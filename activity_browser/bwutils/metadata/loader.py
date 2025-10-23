import subprocess
import sqlite3
import sys
import pickle
from logging import getLogger
from typing import Literal

import pandas as pd
import bw2data as bd
from bw2data.backends import sqlite3_lci_db

from qtpy import QtCore

from activity_browser import signals, application
from activity_browser.ui import threading

from .metadata import MetaDataStore
from .fields import secondary_types, primary, secondary

log = getLogger(__name__)


class MDSLoader(QtCore.QObject):
    primary_status: Literal["idle", "loading", "done"] = "idle"
    secondary_status: Literal["idle", "loading", "done"] = "idle"

    def __init__(self, mds: MetaDataStore):
        super().__init__(mds)

        self.mds = mds
        self.connect_signals()

    def connect_signals(self):
        signals.project.changed.connect(self.on_project_changed)

    def on_project_changed(self):
        self.load_project()

    def load_project(self):
        # set statuses
        self.primary_status = "loading"
        self.secondary_status = "loading"

        # start loading threads
        thread = SecondaryLoadThread(self)
        thread.setObjectName("SecondaryLoadThread-MDSLoader")
        thread.done.connect(self.secondary_load_project)
        thread.start(databases=list(bd.databases), sqlite_db=str(sqlite3_lci_db._filepath))

        # load primary metadata in the main thread
        self.primary_load_project()

    def primary_load_project(self):
        with sqlite3.connect(sqlite3_lci_db._filepath) as con:
            fields = ', '.join(primary[1:])  # Exclude 'key' as it's constructed
            primary_df = pd.read_sql(f"SELECT {fields} FROM activitydataset", con)

        primary_df["key"] = list(zip(primary_df["database"], primary_df["code"]))
        primary_df.index = pd.MultiIndex.from_tuples(primary_df["key"], names=["database", "code"])

        log.debug(f"Primary metadata loaded with {len(primary_df)} rows")
        self.mds.dataframe = primary_df

        for idx in primary_df.index:
            self.mds.register_mutation(idx, "add")
        
        self.primary_status = "done"

    def secondary_load_project(self, secondary_df: pd.DataFrame, sqlite_db: str):
        if sqlite_db != str(sqlite3_lci_db._filepath):
            return

        assert all(secondary_df.index.isin(self.mds.dataframe.index))
        log.debug(f"Secondary metadata loaded with {len(secondary_df)} rows")
        self.mds.dataframe = pd.concat([self.mds.dataframe[primary], secondary_df], axis=1)

        for idx in secondary_df.index:
            self.mds.register_mutation(idx, "update")
        
        self.secondary_status = "done"

    def load_database(self, database_name: str):
        # start loading threads
        thread = SecondaryLoadThread(self)
        thread.done.connect(self.secondary_load_database)
        thread.start(databases=[database_name], sqlite_db=str(sqlite3_lci_db._filepath))

        # load primary metadata in the main thread
        self.primary_load_database(database_name)

    def primary_load_database(self, database_name: str):
        with sqlite3.connect(sqlite3_lci_db._filepath) as con:
            fields = ', '.join(primary[1:])  # Exclude 'key' as it's constructed
            primary_df = pd.read_sql(f"SELECT {fields} FROM activitydataset WHERE database = '{database_name}'", con)

        primary_df["key"] = list(zip(primary_df["database"], primary_df["code"]))
        primary_df.index = pd.MultiIndex.from_tuples(primary_df["key"], names=["database", "code"])

        log.debug(f"Primary metadata loaded with {len(primary_df)} rows")
        self.mds.dataframe = pd.concat([self.mds.dataframe, primary_df])

        for idx in primary_df.index:
            self.mds.register_mutation(idx, "add")

    def secondary_load_database(self, secondary_df: pd.DataFrame, sqlite_db: str):
        if secondary_df.empty or sqlite_db != str(sqlite3_lci_db._filepath):
            return

        database = secondary_df.index[0][0]
        indices = self.mds.dataframe.loc[[database]].index

        if not all(secondary_df.index.isin(indices)):
            log.debug("Secondary database metadata dropping rows")
            secondary_df = secondary_df[secondary_df.index.isin(indices)]

        log.debug(f"Secondary metadata loaded with {len(secondary_df)} rows")

        self._fix_categories(secondary_df)
        self.mds.dataframe.update(secondary_df)

        for idx in secondary_df.index:
            self.mds.register_mutation(idx, "update")

    # utility functions
    def _fix_categories(self, df: pd.DataFrame):
        category_columns = [k for k, v in secondary_types.items() if v == "category"]

        for col in category_columns:
            categories = df[col].dropna().unique()
            categories = [c for c in categories if c not in self.mds.dataframe[col].cat.categories]

            # add new category to column
            self.mds.dataframe[col] = self.mds.dataframe[col].cat.add_categories(categories)


class SecondaryLoadThread(threading.ABThread):
    done: QtCore.SignalInstance = QtCore.Signal(pd.DataFrame, str)

    def run_safely(self, databases: list[str], sqlite_db: str):
        processes = [self.open_load_process(db, sqlite_db) for db in databases]

        full_df = pd.DataFrame()
        for proc in processes:
            stdout_data, stderr_data = proc.communicate()
            if proc.returncode != 0:
                log.error(f"Error loading metadata: {stderr_data.decode()}")
                continue
            df = pickle.loads(stdout_data)
            if df.empty:
                continue

            full_df = pd.concat([full_df, df])

        self.done.emit(full_df, sqlite_db)

    def open_load_process(self, database_name: str, sqlite_db: str) -> subprocess.Popen:
        import activity_browser.bwutils.metadata._sub_loader as sl

        return subprocess.Popen(
            [sys.executable, sl.__file__, str(sqlite_db), database_name] + secondary,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

