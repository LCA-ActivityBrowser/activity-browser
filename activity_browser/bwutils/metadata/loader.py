import subprocess
import sqlite3
import sys
import pickle
from logging import getLogger

import pandas as pd
import bw2data as bd
from bw2data.backends import sqlite3_lci_db

from qtpy import QtCore

from activity_browser import signals, application
from activity_browser.ui import threading

from .metadata import MetaDataStore
from .fields import all, primary, secondary

log = getLogger(__name__)


class MDSLoader(QtCore.QObject):
    def __init__(self, mds: MetaDataStore):
        super().__init__(mds)
        self.moveToThread(application.thread())

        self.mds = mds
        self.connect_signals()

    def connect_signals(self):
        signals.project.changed.connect(self.on_project_changed)
        #
        # signals.node.changed.connect(self.on_node_changed)
        # signals.node.deleted.connect(self.on_node_deleted)

        # signals.meta.databases_changed.connect(self.sync_databases)
        # signals.database.deleted.connect(self.sync_databases)

    def on_project_changed(self):
        # clear existing metadata
        self.mds.dataframe = pd.DataFrame()

        # start loading threads
        thread = SecondaryLoadThread(self)
        thread.done.connect(self.secondary_load_project)
        thread.start()

        # load primary metadata in the main thread
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
        primary_df = pd.read_sql(f"SELECT {', '.join(primary)} FROM activitydataset", con)
        con.close()
        log.debug(f"Primary metadata loaded with {len(primary_df)} rows")
        self.mds.dataframe = pd.concat([self.mds.dataframe, primary_df])

    def secondary_load_project(self, secondary_df: pd.DataFrame):
        assert len(secondary_df) == len(self.mds.dataframe)
        log.debug(f"Secondary metadata loaded with {len(secondary_df)} rows")
        self.mds.dataframe = pd.concat([self.mds.dataframe[primary], secondary_df], axis=1)


class SecondaryLoadThread(threading.ABThread):
    done: QtCore.SignalInstance = QtCore.Signal(pd.DataFrame)

    def run_safely(self, *args, **kwargs):
        processes = [self.open_load_process(db) for db in bd.databases]

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

        self.done.emit(full_df)

    def open_load_process(self, database_name: str):
        import activity_browser.bwutils.metadata._sub_loader as sl

        return subprocess.Popen(
            [sys.executable, sl.__file__, str(sqlite3_lci_db._filepath), database_name] + secondary,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

